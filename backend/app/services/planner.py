from __future__ import annotations

from pydantic import BaseModel

from .gmail_ingest import GmailMessage
from .validator import ValidatedExtraction
from .ai_router import RoutingDecision


class ContactPlan(BaseModel):
  full_name: str
  email: str | None = None


class CompanyPlan(BaseModel):
  name: str
  domain: str | None = None


class NotePlan(BaseModel):
  title: str
  body: str
  external_ref: str


class CrmUpsertPlan(BaseModel):
  contact: ContactPlan | None = None
  company: CompanyPlan | None = None
  note: NotePlan


class DealPlan(BaseModel):
  dealname: str
  amount: str | None = None
  pipeline: str = "default"
  dealstage: str = "appointmentscheduled"
  closedate: str | None = None


class TicketPlan(BaseModel):
  subject: str
  content: str
  priority: str = "MEDIUM"
  pipeline: str = "0"
  pipeline_stage: str = "1"


class OrderPlan(BaseModel):
  reference: str | None = None
  amount: str | None = None
  status: str | None = None


class EnhancedCrmPlan(BaseModel):
  object_type: str
  contact: ContactPlan | None = None
  company: CompanyPlan | None = None
  deal: DealPlan | None = None
  ticket: TicketPlan | None = None
  order: OrderPlan | None = None
  note: NotePlan | None = None
  associations: list[str] = []


def build_crm_plan(email: GmailMessage, extraction: ValidatedExtraction) -> CrmUpsertPlan:
  contact_plan = None
  if extraction.people:
    primary = extraction.people[0]
    contact_plan = ContactPlan(full_name=primary.name, email=primary.email)

  company_plan = None
  if extraction.company:
    company_plan = CompanyPlan(name=extraction.company.name, domain=extraction.company.domain)

  note_lines = [
    f"Summary: {extraction.summary}",
    f"Intent: {extraction.intent or 'N/A'}",
    f"Amount: {extraction.amount or 'N/A'}",
    f"Dates: {', '.join(extraction.dates) if extraction.dates else 'N/A'}",
    f"Next Steps: {', '.join(extraction.next_steps) if extraction.next_steps else 'N/A'}",
    f"Evidence: {extraction.evidence or 'N/A'}",
    "",
    f"ExternalRef: {extraction.message_id}",
  ]

  note_plan = NotePlan(
    title=email.subject or "Email Note",
    body="\n".join(note_lines),
    external_ref=extraction.message_id,
  )

  return CrmUpsertPlan(contact=contact_plan, company=company_plan, note=note_plan)


def build_enhanced_crm_plan(email: GmailMessage, extraction: ValidatedExtraction, routing: RoutingDecision) -> EnhancedCrmPlan:
  base_plan = build_crm_plan(email, extraction)
  order_plan = None
  deal_plan = None
  ticket_plan = None

  if routing.primary_object == "deals" and extraction.amount:
    deal_plan = DealPlan(
      dealname=email.subject or "New deal",
      amount=str(extraction.amount),
      dealstage="appointmentscheduled",
      pipeline="default",
    )
  if routing.primary_object == "tickets":
    ticket_plan = TicketPlan(
      subject=email.subject or "Support request",
      content=extraction.summary or extraction.evidence or email.body_text or "",
      priority="MEDIUM",
      pipeline="0",
      pipeline_stage="1",
    )
  if routing.primary_object == "orders":
    order_plan = OrderPlan(
      reference=routing.suggested_properties.get("order", {}).get("reference") if isinstance(routing.suggested_properties, dict) else None,
      amount=str(extraction.amount) if extraction.amount else None,
      status="processing",
    )

  return EnhancedCrmPlan(
    object_type=routing.primary_object,
    contact=base_plan.contact,
    company=base_plan.company,
    deal=deal_plan,
    ticket=ticket_plan,
    order=order_plan,
    note=base_plan.note if routing.create_note else None,
    associations=[],
  )
