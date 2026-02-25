"""Playwright automation for the National Cyber Crime Reporting Portal."""

import asyncio
from datetime import datetime, timezone

from config.constants import PORTAL_SELECTORS, ComplaintStatus
from config.logging_config import get_logger
from config.settings import Settings
from nyaynet.common.audit_logger import AuditLogger
from nyaynet.common.exceptions import FilingError, PortalNavigationError
from nyaynet.common.utils import utc_now_iso
from nyaynet.evidence.models import EvidencePackage
from nyaynet.filing.captcha_handler import CaptchaHandler
from nyaynet.filing.form_filler import FormFiller
from nyaynet.filing.models import ComplaintSubmission, FilingResult
from nyaynet.filing.otp_handler import OTPHandler
from nyaynet.storage.file_store import FileStore
from nyaynet.storage.repositories import ComplaintRepository

log = get_logger(__name__)

PORTAL_URL = "https://cybercrime.gov.in"


class PortalAutomator:
    """Full Playwright workflow for filing on cybercrime.gov.in."""

    def __init__(
        self,
        settings: Settings,
        complaint_repo: ComplaintRepository,
        file_store: FileStore,
        audit_logger: AuditLogger,
        otp_handler: OTPHandler | None = None,
        captcha_handler: CaptchaHandler | None = None,
    ):
        self._settings = settings
        self._repo = complaint_repo
        self._file_store = file_store
        self._audit = audit_logger
        self._otp = otp_handler or OTPHandler()
        self._captcha = captcha_handler or CaptchaHandler()
        self._form_filler = FormFiller()

    def file_complaint(self, package: EvidencePackage) -> FilingResult:
        """File a complaint on the cyber crime portal (synchronous wrapper)."""
        return asyncio.run(self._file_complaint_async(package))

    async def _file_complaint_async(self, package: EvidencePackage) -> FilingResult:
        """Async implementation of complaint filing."""
        result = FilingResult(
            evidence_package_id=package.id,
            status=ComplaintStatus.FILING_IN_PROGRESS,
        )

        # Create DB record
        self._repo.insert(result.to_db_dict())

        self._audit.log(
            action="filing_started",
            entity_type="complaint",
            entity_id=result.id,
            details={"evidence_package_id": package.id, "username": package.username},
        )

        try:
            from playwright.async_api import async_playwright

            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=False)  # Visible for user interaction
                context = await browser.new_context(
                    viewport={"width": 1280, "height": 720},
                )
                page = await context.new_page()

                # Step 1: Navigate to portal
                log.info("navigating_to_portal")
                await page.goto(PORTAL_URL, wait_until="networkidle", timeout=60000)
                await self._screenshot(page, package.username, "01_portal_home")

                # Step 2: Navigate to complaint filing page
                log.info("navigating_to_filing_page")
                await page.click("text=File a Complaint", timeout=15000)
                await page.wait_for_load_state("networkidle")
                await self._screenshot(page, package.username, "02_filing_page")

                # Step 3: Accept terms if present
                try:
                    accept_btn = page.locator("text=I Accept")
                    if await accept_btn.is_visible(timeout=5000):
                        await accept_btn.click()
                        await page.wait_for_load_state("networkidle")
                except Exception:
                    pass  # Terms page may not always appear

                # Step 4: OTP verification
                log.info("handling_otp")
                otp = self._otp.get_otp("Enter OTP sent to your registered mobile/email")
                try:
                    await page.fill(PORTAL_SELECTORS["otp_input"], otp)
                    await page.click(PORTAL_SELECTORS["otp_submit"])
                    await page.wait_for_load_state("networkidle")
                    await self._screenshot(page, package.username, "03_otp_verified")
                except Exception as e:
                    log.warning("otp_step_issue", error=str(e))

                # Step 5: Build submission data
                submission = ComplaintSubmission(
                    complainant_name=self._settings.portal_complainant_name,
                    complainant_email=self._settings.portal_complainant_email,
                    complainant_phone=self._settings.portal_complainant_phone,
                    complainant_state=self._settings.portal_complainant_state,
                    complainant_city=self._settings.portal_complainant_city,
                    category="Women/Child Related Crime",
                    subcategory="Cyber Bullying/Stalking/Sexting",
                    description=package.complaint_text or "Online harassment complaint",
                    incident_date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                    evidence_files=[package.report_path] if package.report_path else [],
                )

                # Step 6: Fill complainant details
                log.info("filling_complainant_details")
                await self._form_filler.fill_complainant_details(page, submission)
                await self._screenshot(page, package.username, "04_complainant_filled")

                # Step 7: Fill incident details
                log.info("filling_incident_details")
                await self._form_filler.fill_incident_details(page, submission)
                await self._screenshot(page, package.username, "05_incident_filled")

                # Step 8: Upload evidence
                if submission.evidence_files:
                    log.info("uploading_evidence")
                    await self._form_filler.upload_evidence(page, submission.evidence_files)
                    await self._screenshot(page, package.username, "06_evidence_uploaded")

                # Step 9: Handle CAPTCHA if present
                captcha_solution = await self._captcha.detect_and_solve(page)
                if captcha_solution:
                    await page.fill(PORTAL_SELECTORS["captcha_input"], captcha_solution)

                # Step 10: Screenshot before submit (for review)
                await self._screenshot(page, package.username, "07_pre_submit")

                # Step 11: Submit
                log.info("submitting_complaint")
                await page.click(PORTAL_SELECTORS["submit_button"])
                await page.wait_for_load_state("networkidle", timeout=30000)
                await self._screenshot(page, package.username, "08_submitted")

                # Step 12: Extract complaint ID
                try:
                    complaint_id_elem = page.locator(PORTAL_SELECTORS["complaint_id_display"])
                    if await complaint_id_elem.is_visible(timeout=10000):
                        portal_complaint_id = await complaint_id_elem.text_content()
                        result.portal_complaint_id = portal_complaint_id
                        log.info("complaint_id_received", complaint_id=portal_complaint_id)
                except Exception:
                    log.warning("could_not_extract_complaint_id")

                # Capture confirmation screenshot
                confirmation_path = await self._screenshot(
                    page, package.username, "09_confirmation"
                )
                result.confirmation_screenshot = confirmation_path
                result.status = ComplaintStatus.FILED
                result.filed_at = utc_now_iso()
                result.submission_data = {
                    "category": submission.category,
                    "subcategory": submission.subcategory,
                    "incident_date": submission.incident_date,
                }

                await browser.close()

        except ImportError:
            raise FilingError("Playwright is not installed. Run: playwright install chromium")
        except Exception as e:
            result.status = ComplaintStatus.FILING_FAILED
            result.portal_response = str(e)
            log.error("filing_failed", error=str(e))

            self._audit.log(
                action="filing_failed",
                entity_type="complaint",
                entity_id=result.id,
                details={"error": str(e)},
            )

        # Update DB
        self._repo.update_status(
            result.id,
            result.status.value,
            portal_complaint_id=result.portal_complaint_id,
            portal_response=result.portal_response,
            confirmation_screenshot=result.confirmation_screenshot,
            filed_at=result.filed_at,
        )

        if result.status == ComplaintStatus.FILED:
            self._audit.log(
                action="complaint_filed",
                entity_type="complaint",
                entity_id=result.id,
                details={
                    "portal_complaint_id": result.portal_complaint_id,
                    "evidence_package_id": package.id,
                },
            )

        return result

    async def _screenshot(self, page, username: str, label: str) -> str:
        """Take a timestamped screenshot."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = f"filing_{label}_{timestamp}.png"
        screenshot_bytes = await page.screenshot(full_page=False)
        return self._file_store.save_screenshot(username, filename, screenshot_bytes)
