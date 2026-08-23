"""Generate SettleMatch pitch deck PDF (presentation style, no code)."""

from pathlib import Path

from fpdf import FPDF

OUT = Path(__file__).resolve().parents[1] / "SettleMatch_Pitch_Deck.pdf"


class Deck(FPDF):
    def header(self):
        if self.page_no() == 1:
            return
        self.set_font("Helvetica", "I", 9)
        self.set_text_color(100, 100, 100)
        self.cell(0, 8, "SettleMatch  |  Razorpay AI Buildathon  |  Track 04", align="L")
        self.ln(12)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(140, 140, 140)
        self.cell(0, 10, f"{self.page_no()}", align="C")

    def slide_title(self, title: str):
        self.add_page()
        self.set_fill_color(15, 23, 42)
        self.rect(0, 0, 210, 28, "F")
        self.set_xy(14, 8)
        self.set_font("Helvetica", "B", 18)
        self.set_text_color(255, 255, 255)
        self.cell(0, 12, title)
        self.ln(28)
        self.set_text_color(30, 30, 30)

    def h2(self, text: str):
        self.set_font("Helvetica", "B", 13)
        self.set_text_color(15, 23, 42)
        self.multi_cell(0, 8, text)
        self.ln(2)
        self.set_text_color(30, 30, 30)

    def body(self, text: str):
        self.set_font("Helvetica", "", 11)
        self.multi_cell(0, 6.5, text)
        self.ln(2)

    def bullet(self, text: str):
        self.set_font("Helvetica", "", 11)
        self.set_x(18)
        self.multi_cell(0, 6.5, f"-  {text}")

    def quote(self, text: str):
        self.set_fill_color(241, 245, 249)
        self.set_font("Helvetica", "I", 12)
        self.set_text_color(30, 41, 59)
        y = self.get_y()
        self.set_xy(14, y)
        self.multi_cell(182, 8, f'"{text}"', fill=True)
        self.ln(4)
        self.set_text_color(30, 30, 30)

    def kpi_row(self, items: list[tuple[str, str]]):
        w = 182 / len(items)
        x0 = 14
        y = self.get_y()
        for i, (label, value) in enumerate(items):
            x = x0 + i * w
            self.set_xy(x, y)
            self.set_fill_color(248, 250, 252)
            self.rect(x, y, w - 3, 22, "F")
            self.set_xy(x + 2, y + 2)
            self.set_font("Helvetica", "B", 14)
            self.set_text_color(15, 23, 42)
            self.cell(w - 7, 8, value)
            self.set_xy(x + 2, y + 11)
            self.set_font("Helvetica", "", 8)
            self.set_text_color(100, 116, 139)
            self.cell(w - 7, 6, label)
        self.set_y(y + 28)
        self.set_text_color(30, 30, 30)


def build() -> Path:
    pdf = Deck(format="A4")
    pdf.set_auto_page_break(auto=True, margin=18)

    # Cover
    pdf.add_page()
    pdf.set_fill_color(15, 23, 42)
    pdf.rect(0, 0, 210, 297, "F")
    pdf.set_text_color(148, 163, 184)
    pdf.set_font("Helvetica", "", 12)
    pdf.set_xy(20, 70)
    pdf.cell(0, 8, "RAZORPAY AI BUILDATHON  |  TRACK 04")
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 36)
    pdf.set_xy(20, 90)
    pdf.cell(0, 16, "SettleMatch")
    pdf.set_font("Helvetica", "", 16)
    pdf.set_xy(20, 112)
    pdf.multi_cell(170, 8, "AI Finance Controller for Razorpay Settlements")
    pdf.set_font("Helvetica", "", 12)
    pdf.set_text_color(148, 163, 184)
    pdf.set_xy(20, 150)
    pdf.multi_cell(
        170,
        7,
        "Build. Show. Get hired.\n"
        "Product pitch deck  |  Features and story  |  No code",
    )
    pdf.set_xy(20, 240)
    pdf.set_font("Helvetica", "I", 11)
    pdf.cell(0, 8, "Rules first.  AI second.  Gate always.")

    pdf.slide_title("01  |  The Problem")
    pdf.h2("Money arrives in two places")
    pdf.bullet("Razorpay settlement list")
    pdf.bullet("Bank statement credits")
    pdf.ln(3)
    pdf.h2("Finance teams still match them by hand")
    pdf.bullet("Slow")
    pdf.bullet("Error-prone")
    pdf.bullet("Hard to audit")
    pdf.bullet("Easy to miss missing credits")

    pdf.slide_title("02  |  The Opportunity")
    pdf.body(
        "AI can generate answers fast. Finance needs something else: "
        "verification capacity."
    )
    pdf.ln(2)
    pdf.quote(
        "The question is not 'Can AI talk?' - it is 'Can AI close the books safely?'"
    )
    pdf.body(
        "Track 04 (AI Finance Controller) asks builders to close one finance-ops loop "
        "on a 50+ record batch, with measured accuracy and an honest exception list."
    )

    pdf.slide_title("03  |  What We Built")
    pdf.h2("SettleMatch closes one full finance loop")
    pdf.bullet("Take settlements + bank rows")
    pdf.bullet("Match them automatically")
    pdf.bullet("Show match rate")
    pdf.bullet("List what it could not resolve")
    pdf.bullet("Keep a full audit trail")
    pdf.ln(3)
    pdf.quote("One job. Done end-to-end.")

    pdf.slide_title("04  |  Product Promise")
    pdf.bullet("Every match is explainable")
    pdf.bullet("Every money-adjacent decision is bounded")
    pdf.bullet("Ambiguous cases are refused - never guessed")
    pdf.ln(4)
    pdf.body("That is the Track 04 bar - and SettleMatch is designed around it.")

    pdf.slide_title("05  |  How It Works")
    pdf.h2("Three layers")
    pdf.ln(1)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "1. Rules engine", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11)
    pdf.multi_cell(0, 6.5, "Clear cases first (UTR, amount + date window).")
    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "2. AI matcher", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11)
    pdf.multi_cell(0, 6.5, "Only leftovers and messy narration cases.")
    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "3. Confidence gate", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11)
    pdf.multi_cell(0, 6.5, "Low confidence becomes an exception - not an auto-approve.")
    pdf.ln(4)
    pdf.quote("Smart + safe.")

    pdf.slide_title("06  |  Key Features")
    pdf.bullet("Batch reconciliation on 100 synthetic records")
    pdf.bullet("Dual matching: Rules + AI")
    pdf.bullet("Confidence threshold (0.85)")
    pdf.bullet("Honest exception list with reasons")
    pdf.bullet("Full audit log of every decision")
    pdf.bullet("Live dashboard for demos")
    pdf.bullet("Eval metrics against ground truth")
    pdf.bullet("Gemini-ready; offline heuristic fallback for demos")

    pdf.slide_title("07  |  Demo Flow")
    pdf.bullet("Load settlement + bank data")
    pdf.bullet("Click Run reconciliation")
    pdf.bullet("See match rate, rupees matched, rule vs AI split")
    pdf.bullet("Review exceptions with reasons")
    pdf.bullet("Open audit trail - every decision explained")
    pdf.ln(4)
    pdf.body(
        "Ideal for a 5-minute pitch video: problem -> live run -> metrics -> refuse case."
    )

    pdf.slide_title("08  |  Results (Sample Batch)")
    pdf.body("On a batch of 100 settlements:")
    pdf.ln(2)
    pdf.kpi_row(
        [
            ("Match rate", "90%"),
            ("Rule / AI", "75 / 15"),
            ("Exceptions", "10"),
            ("False matches", "0"),
        ]
    )
    pdf.body(
        "Signal for reviewers: high accuracy, clear AI contribution, "
        "and honest unresolved cases - not a cherry-picked demo."
    )

    pdf.slide_title("09  |  Why This Wins Track 04")
    pdf.body("The track asks for:")
    pdf.bullet("Throughput on a real batch")
    pdf.bullet("Measured accuracy")
    pdf.bullet("An honest exception list")
    pdf.ln(3)
    pdf.body("SettleMatch delivers all three - not a chatbot wrapper.")

    pdf.slide_title("10  |  Why Razorpay")
    pdf.bullet("Settlements")
    pdf.bullet("Merchant money movement")
    pdf.bullet("Finance operations")
    pdf.bullet("Trust and auditability in payments")
    pdf.ln(3)
    pdf.body("Looks like real Razorpay work - not a generic AI toy.")

    pdf.slide_title("11  |  Safety and Trust")
    pdf.bullet("AI cannot invent bank IDs outside the candidate list")
    pdf.bullet("Already-used bank rows cannot be rematched")
    pdf.bullet("Below-threshold suggestions are refused")
    pdf.bullet("Every accept / refuse is logged")
    pdf.ln(3)
    pdf.quote("Failure mode shown: graceful refuse.")

    pdf.slide_title("12  |  Who It Is For")
    pdf.bullet("Merchant finance teams")
    pdf.bullet("Ops / reconciliation analysts")
    pdf.bullet("Future: Razorpay internal finance tooling")
    pdf.ln(3)
    pdf.body(
        "Internship angle: a builder who ships bounded AI systems - "
        "not someone who only prompts models."
    )

    pdf.slide_title("13  |  What Is Next")
    pdf.bullet("Live Razorpay settlement APIs")
    pdf.bullet("Multi-account / multi-currency support")
    pdf.bullet("Human-in-the-loop review queue")
    pdf.bullet("Production dashboards and alerts")

    pdf.slide_title("14  |  Closing")
    pdf.ln(8)
    pdf.set_font("Helvetica", "B", 16)
    pdf.multi_cell(0, 9, "SettleMatch does not just find matches.")
    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 16)
    pdf.multi_cell(0, 9, "It closes the books - with proof.")
    pdf.ln(10)
    pdf.quote("Rules first. AI second. Gate always.")
    pdf.ln(6)
    pdf.h2("30-second spoken version")
    pdf.body(
        "SettleMatch is an AI finance controller. It reconciles Razorpay settlements "
        "with bank credits. Clear cases are matched by rules, messy cases by AI, and "
        "anything uncertain is refused with an audit trail. On 100 records we hit 90% "
        "match with zero false matches and 10 honest exceptions."
    )

    pdf.output(OUT)
    return OUT


if __name__ == "__main__":
    path = build()
    print(f"Wrote {path}")
