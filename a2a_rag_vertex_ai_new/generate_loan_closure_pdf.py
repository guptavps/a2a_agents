import argparse
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


GENERAL_CONTROLS = [
    ("Closure authority", "Only an employee with the required servicing authority may approve final closure. The preparer and approver must be different people unless a documented low-risk exception permits single-person processing."),
    ("Identity and account match", "Match the account number, borrower or obligor identity, product record, and signed agreement before relying on any payment, collateral, or release information."),
    ("Financial completion", "The ledger must show a zero principal balance, settled interest, resolved fees, completed reversals, and no pending payment, adjustment, suspense, or chargeback activity."),
    ("Legal and operational holds", "Bankruptcy flags, litigation holds, fraud investigations, sanctions concerns, servicing transfers, deceased-borrower workflows, and regulatory restrictions must be resolved or formally released before closure."),
    ("Customer notification", "Provide accurate confirmation identifying the effective date, administrative actions, refund or release expectations, and the channel for disputes."),
    ("Evidence retention", "Preserve the final statement, payment evidence, approval record, release evidence, customer communication, exception decisions, and relevant system audit identifiers."),
]


LOAN_TYPE_POLICIES = [
    ("Residential mortgage loans", "First-lien and junior-lien residential mortgages secured by a completed dwelling.", [
        "Confirm the payoff quote was valid on the date funds settled and daily interest was calculated through the actual payoff date.",
        "Reconcile principal, accrued interest, late charges, escrow advances, recording fees, and permitted payoff fees.",
        "Complete escrow analysis and determine whether the remaining balance is due to the borrower or transferred under an approved process.",
        "Verify the lien release or satisfaction package names the correct borrower, county, and legal description.",
        "Review subordinate liens, loss mitigation, foreclosure, insurance, and tax workflows before marking the mortgage closed.",
    ], "Retain the payoff statement, settlement confirmation, transaction history, escrow disposition, lien-release request, customer notice, and approval record."),
    ("FHA-insured loans", "Loans insured under an FHA program and subject to program-specific insurance handling.", [
        "Match the FHA case identifier and mortgage record to the account being closed.",
        "Verify mortgage insurance premium treatment is consistent across the servicing platform and settlement records.",
        "Check for partial-claim, loss-mitigation, escrow, or subordinate-financing records that prevent routine satisfaction.",
        "Follow the applicable jurisdiction and FHA servicing procedure for the recorded satisfaction.",
    ], "Retain the FHA case reference, payoff calculation, insurance reconciliation, lien-release evidence, and exception approval."),
    ("VA-guaranteed loans", "VA-guaranteed residential loans requiring verification of guarantee-related servicing data.", [
        "Match the VA loan identifier and guaranty information before closure approval.",
        "Confirm accrued amounts, funding-fee treatment, and escrow adjustments are documented.",
        "Review assumptions, substitutions of entitlement, or special servicing records requiring agency processing.",
        "Direct the lien satisfaction to the correct jurisdiction and provide a clear closure statement.",
    ], "Retain VA identifiers, payoff statement, final ledger, agency correspondence, release documentation, and customer notification."),
    ("USDA-guaranteed loans", "USDA rural housing loans requiring additional attention to guarantee and escrow records.", [
        "Validate the USDA loan reference and property record against the servicing account.",
        "Reconcile escrow funds, annual fee treatment, tax and insurance advances, and final payoff amount.",
        "Resolve special servicing status, transfer restrictions, or agency communications before closure.",
        "Complete the satisfaction process with the correct borrower names and legal description.",
    ], "Retain the USDA reference, payoff computation, escrow reconciliation, agency correspondence, release record, and approval evidence."),
    ("Jumbo and portfolio mortgage loans", "Mortgages outside standard agency limits or held in a lender portfolio.", [
        "Review the note, rider, and servicing agreement for payoff fees, prepayment provisions, and notice requirements.",
        "Reconcile participation, warehouse, investor, or custodial balances before internal closure.",
        "Independently review large-dollar settlement and unusual funding sources or same-day corrections.",
        "Coordinate collateral release with the party responsible for the original note and security instrument.",
    ], "Retain the governing agreement, investor reconciliation, settlement evidence, payoff approval, and release package."),
    ("Home equity lines of credit", "Revolving home-secured credit facilities, whether open, frozen, or fully repaid.", [
        "Confirm available credit is zero, the line is formally closed, and no additional draw channel remains active.",
        "Resolve pending debit-card, check, ACH, transfer, or bill-pay activity associated with the line.",
        "Reconcile variable-rate interest, annual fees, and early-termination provisions.",
        "Prepare the correct release or modification document for the security instrument.",
    ], "Retain the zero-balance statement, closure status, pending-transaction review, fee reconciliation, and lien documentation."),
    ("Construction and renovation loans", "Construction facilities, renovation draws, and loans converting to permanent financing.", [
        "Reconcile approved draws, inspection invoices, retainage, interest reserves, and unused commitments.",
        "Confirm completion certificates, occupancy evidence, title updates, and final inspections where applicable.",
        "Determine whether closure is by payoff, conversion, refinance, or approved replacement loan.",
        "Resolve contractor claims, mechanics-lien notices, insurance gaps, and disbursement exceptions.",
    ], "Retain draw history, inspection records, title evidence, completion approval, final ledger, lien review, and conversion or payoff documents."),
    ("Bridge and hard-money loans", "Short-term property-secured facilities with customized maturity, extension, and exit provisions.", [
        "Review the agreement for extension fees, exit fees, default interest, minimum interest, and payoff notice requirements.",
        "Confirm the exit transaction funded and obtain reliable settlement evidence from the replacement lender or title company.",
        "Reconcile protective advances, property expenses, legal fees, and interest reserves.",
        "Release the security instrument only after settlement funds are irrevocably received.",
    ], "Retain the payoff quote, settlement statement, funding confirmation, advance reconciliation, and release instructions."),
    ("Commercial real estate loans", "Loans secured by office, retail, industrial, multifamily, and mixed-use assets.", [
        "Verify borrowing entity, guarantors, property legal description, and authorized signatories against closing documents.",
        "Reconcile interest, reserves, taxes, insurance, operating-income escrows, defeasance, yield maintenance, and legal costs.",
        "Resolve lender-held originals, participation interests, environmental obligations, and covenant monitoring records.",
        "Coordinate releases for mortgages, assignments of leases and rents, fixture filings, UCC statements, and guarantees.",
    ], "Retain entity authorization, payoff computation, reserve reconciliation, title and UCC releases, and investor approvals."),
    ("Lombard and securities-backed loans", "Credit facilities secured by brokerage assets, securities accounts, pledged portfolios, or eligible investment collateral.", [
        "Confirm the facility balance, accrued interest, commitment fees, margin charges, and maintenance charges are settled.",
        "Obtain a current collateral statement and verify pledged positions, account controls, and transfer restrictions.",
        "Check unsettled trades, corporate actions, dividends, withholding adjustments, restricted securities, and pending transfers.",
        "Confirm the custodian or account controller releases the pledge only after irrevocable payment and authorized instructions.",
        "Reconcile collateral substitution, forced liquidation, shortfall, or excess-proceeds events separately from the payoff ledger.",
        "Protect portfolio information and require dual authorization for high-value release instructions.",
    ], "Retain the final ledger, collateral inventory, custodian confirmation, pledge-release instruction, settlement evidence, and approval trail."),
    ("Equipment and asset-backed loans", "Loans secured by vehicles, machinery, aircraft, vessels, inventory, or other identifiable business assets.", [
        "Match collateral serial numbers, titles, registrations, schedules, and valuation records to the loan.",
        "Resolve insurance claims, repossession activity, repairs, location changes, and collateral substitutions.",
        "Prepare UCC, title, registry, and filing-office releases for every applicable jurisdiction and asset class.",
        "Distinguish ownership transfer from lien release and document the correct asset disposition.",
    ], "Retain the asset schedule, payoff statement, inspection or disposition evidence, filing releases, titles, and customer notice."),
    ("Auto loans", "Consumer and commercial vehicle loans secured by titled motor vehicles.", [
        "Verify vehicle identification number, title jurisdiction, registered owner, payoff amount, and payment settlement.",
        "Resolve pending payments, insurance claims, total-loss proceeds, repossession costs, storage charges, and title corrections.",
        "Release the lien through the approved electronic or paper title process.",
        "Issue any surplus refund only after the final ledger and title status are reconciled.",
    ], "Retain the payoff statement, VIN verification, settlement record, lien-release confirmation, title evidence, and refund record."),
    ("Personal and unsecured loans", "Unsecured installment loans and personal credit facilities without pledged collateral.", [
        "Confirm contractual payoff amount and resolve accrued interest, payment reversals, fees, hardship balances, and modifications.",
        "Terminate recurring payments, autopay instructions, linked payment tokens, and collection activities appropriately.",
        "Review identity, fraud, dispute, and chargeback status before final closure.",
        "Provide the final statement and clearly indicate that no collateral release applies.",
    ], "Retain the final statement, payment settlement, recurring-payment cancellation, dispute review, and customer communication."),
]


def styles():
    result = getSampleStyleSheet()
    result.add(ParagraphStyle(name="TitleCenter", parent=result["Title"], alignment=TA_CENTER, spaceAfter=18))
    result.add(ParagraphStyle(name="Section", parent=result["Heading1"], fontSize=15, leading=18, spaceBefore=14, spaceAfter=8))
    result.add(ParagraphStyle(name="Subsection", parent=result["Heading2"], fontSize=11, leading=14, spaceBefore=8, spaceAfter=4))
    result.add(ParagraphStyle(name="BodySmall", parent=result["BodyText"], fontSize=9, leading=13, spaceAfter=6))
    return result


def footer(pdf: canvas.Canvas, document) -> None:
    pdf.saveState()
    pdf.setFont("Helvetica", 7)
    pdf.setFillColor(colors.grey)
    pdf.drawString(0.7 * inch, 0.4 * inch, "Loan Closure Policy | Controlled document")
    pdf.drawRightString(7.8 * inch, 0.4 * inch, f"Page {document.page}")
    pdf.restoreState()


def generate_loan_closure_pdf(output_path: str | Path) -> int:
    """Generate a detailed, non-repetitive loan-closure policy PDF locally."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    document_styles = styles()
    story = [
        Paragraph("Loan Closure Policy Handbook", document_styles["TitleCenter"]),
        Paragraph("Policy ID: LCP-001 | Version: 1.0 | Effective date: 2026-09-24", document_styles["BodySmall"]),
        Paragraph("This handbook defines closure controls for secured, unsecured, residential, commercial, investment-backed, and specialty lending products. It is a generated test document for document-ingestion validation; operational teams must replace it with an approved policy source before production use.", document_styles["BodySmall"]),
        Paragraph("1. Enterprise Closure Framework", document_styles["Section"]),
    ]
    for title, text in GENERAL_CONTROLS:
        story.extend([Paragraph(title, document_styles["Subsection"]), Paragraph(text, document_styles["BodySmall"])])

    story.extend([
        Paragraph("2. Product-Specific Closure Procedures", document_styles["Section"]),
        Paragraph("The following procedures supplement the enterprise controls. When a product rule conflicts with a general control, the stricter requirement applies unless an authorized exception is documented.", document_styles["BodySmall"]),
    ])

    for number, (name, scope, controls, evidence) in enumerate(LOAN_TYPE_POLICIES, start=1):
        story.append(Paragraph(f"2.{number} {name}", document_styles["Subsection"]))
        story.append(Paragraph(f"<b>Scope:</b> {scope}", document_styles["BodySmall"]))
        rows = [[Paragraph("Control", document_styles["BodySmall"]), Paragraph("Required action", document_styles["BodySmall"])]]
        rows.extend([[str(control_number), Paragraph(control, document_styles["BodySmall"])] for control_number, control in enumerate(controls, start=1)])
        table = Table(rows, colWidths=[0.55 * inch, 6.55 * inch], repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#D9EAF7")),
            ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#9AA7B2")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.extend([table, Spacer(1, 8), Paragraph(f"<b>Evidence:</b> {evidence}", document_styles["BodySmall"])])

    story.extend([
        Paragraph("3. Exception and Escalation Workflow", document_styles["Section"]),
        Paragraph("A closure exception must identify the account, failed control, customer or collateral impact, containment, owner, due date, approving authority, and resolution. The account remains in a controlled pending-closure state until resolution or an authorized decision permits closure.", document_styles["BodySmall"]),
        Paragraph("4. Audit and Quality Review", document_styles["Section"]),
        Paragraph("Quality review should sample closed accounts across products, risk tiers, channels, and processing teams. Review both the financial result and evidence trail, including whether a release was directed to the correct asset, entity, custodian, county, registry, or filing office.", document_styles["BodySmall"]),
        Paragraph("5. Customer Dispute Handling", document_styles["Section"]),
        Paragraph("A post-closure dispute must be linked to the original closure package. Preserve the account state, investigate the disputed transaction or release, communicate the outcome, and correct the ledger or external filing when an error is confirmed.", document_styles["BodySmall"]),
    ])

    document = SimpleDocTemplate(str(path), pagesize=letter, rightMargin=0.7 * inch, leftMargin=0.7 * inch, topMargin=0.65 * inch, bottomMargin=0.65 * inch, title="Loan Closure Policy Handbook", author="Loan Servicing Policy Team")
    document.build(story, onFirstPage=footer, onLaterPages=footer)
    return path.stat().st_size


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a detailed local loan-closure policy PDF.")
    parser.add_argument("output_path", type=Path)
    args = parser.parse_args()
    size = generate_loan_closure_pdf(args.output_path)
    print(f"Created {args.output_path} ({size} bytes)")


if __name__ == "__main__":
    main()
