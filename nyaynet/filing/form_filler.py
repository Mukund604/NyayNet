"""Field-level form handlers for the cyber crime portal."""

from config.constants import PORTAL_SELECTORS
from config.logging_config import get_logger
from nyaynet.common.exceptions import FormSubmissionError
from nyaynet.filing.models import ComplaintSubmission

log = get_logger(__name__)


class FormFiller:
    """Fills individual form fields on the cyber crime portal."""

    async def fill_complainant_details(self, page, submission: ComplaintSubmission) -> None:
        """Fill in complainant personal details."""
        try:
            await self._fill_field(page, PORTAL_SELECTORS["name_input"], submission.complainant_name)
            await self._fill_field(page, PORTAL_SELECTORS["email_input"], submission.complainant_email)
            await self._fill_field(page, PORTAL_SELECTORS["phone_input"], submission.complainant_phone)
            await self._select_dropdown(page, PORTAL_SELECTORS["state_dropdown"], submission.complainant_state)
            await self._fill_field(page, PORTAL_SELECTORS["city_input"], submission.complainant_city)
            log.info("complainant_details_filled")
        except Exception as e:
            raise FormSubmissionError(f"Failed to fill complainant details: {e}") from e

    async def fill_incident_details(self, page, submission: ComplaintSubmission) -> None:
        """Fill in incident/complaint details."""
        try:
            await self._select_dropdown(page, PORTAL_SELECTORS["category_dropdown"], submission.category)
            await self._select_dropdown(page, PORTAL_SELECTORS["subcategory_dropdown"], submission.subcategory)
            await self._fill_field(page, PORTAL_SELECTORS["description_textarea"], submission.description)
            await self._fill_field(page, PORTAL_SELECTORS["incident_date"], submission.incident_date)
            log.info("incident_details_filled")
        except Exception as e:
            raise FormSubmissionError(f"Failed to fill incident details: {e}") from e

    async def upload_evidence(self, page, file_paths: list[str]) -> None:
        """Upload evidence files."""
        if not file_paths:
            return
        try:
            file_input = page.locator(PORTAL_SELECTORS["file_upload"])
            await file_input.set_input_files(file_paths)
            log.info("evidence_files_uploaded", count=len(file_paths))
        except Exception as e:
            raise FormSubmissionError(f"Failed to upload evidence: {e}") from e

    async def _fill_field(self, page, selector: str, value: str) -> None:
        """Fill a text input field."""
        field = page.locator(selector)
        await field.wait_for(state="visible", timeout=10000)
        await field.fill(value)

    async def _select_dropdown(self, page, selector: str, value: str) -> None:
        """Select a dropdown option."""
        dropdown = page.locator(selector)
        await dropdown.wait_for(state="visible", timeout=10000)
        await dropdown.select_option(label=value)
