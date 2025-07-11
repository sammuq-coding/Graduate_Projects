import streamlit as st
import os
import openai
import PyPDF2
import re
from fpdf import FPDF
from io import BytesIO

openai.api_key = "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"

st.set_page_config(page_title="TaxGPT", layout="centered")
st.title("🧾 TaxGPT - Your Tax Assistant")

if "messages" not in st.session_state:
    st.session_state["messages"] = [
        {"role": "system", "content": "You are TaxGPT, a helpful U.S. tax assistant. You help users understand tax documents, summarize content, and extract key fields like name, income, and SSN. Do not provide legal advice."}
    ]

STANDARD_DEDUCTIONS = {
    "Single": 13850,
    "Married Filing Jointly": 27700,
    "Head of Household": 20800
}

def bracket_breakdown(income, status):
    brackets = []
    if status == "Married Filing Jointly":
        levels = [(0, 22000, 0.10), (22000, 89450, 0.12), (89450, 190750, 0.22)]
    else:
        levels = [(0, 11000, 0.10), (11000, 44725, 0.12), (44725, 95375, 0.22)]
    remaining = income
    for low, high, rate in levels:
        if income > low:
            taxable = min(remaining, high - low)
            tax = taxable * rate
            brackets.append((low, high, rate, taxable, tax))
            remaining -= taxable
    return brackets

def estimate_tax_with_breakdown(income, deduction, status):
    try:
        income = float(income)
        taxable_income = income - deduction
        if taxable_income <= 0:
            return 0, []
        breakdown = bracket_breakdown(taxable_income, status)
        total = sum(b[4] for b in breakdown)
        return total, breakdown
    except:
        return "Could not estimate tax from income.", []

def generate_pdf(filing_status, total_income, deduction, estimated_tax, breakdown):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Tax Summary Report", ln=True, align="C")
    pdf.set_font("Arial", "", 12)
    pdf.ln(10)
    pdf.cell(0, 10, f"Filing Status: {filing_status}", ln=True)
    pdf.cell(0, 10, f"Total Income: ${total_income:,.2f}", ln=True)
    pdf.cell(0, 10, f"Standard Deduction: ${deduction:,.2f}", ln=True)
    pdf.cell(0, 10, f"Estimated Tax Owed: ${estimated_tax:,.2f}", ln=True)
    pdf.ln(10)
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "Bracket-by-Bracket Breakdown", ln=True)
    pdf.set_font("Arial", "", 12)
    for low, high, rate, amount, owed in breakdown:
        pdf.cell(0, 10, f"${low:,}–${high:,} at {int(rate * 100)}%: Taxed on ${amount:,.2f} → ${owed:,.2f}", ln=True)

    # Proper in-memory generation for Streamlit
    pdf_output = pdf.output(dest="S").encode("latin-1")
    return BytesIO(pdf_output)

filing_status = st.selectbox("Select your filing status:", list(STANDARD_DEDUCTIONS.keys()))
standard_deduction = STANDARD_DEDUCTIONS[filing_status]
st.markdown(f"📉 **Standard Deduction Applied**: ${standard_deduction:,}")

uploaded_files = st.file_uploader("Upload one or more W-2 PDFs", type="pdf", accept_multiple_files=True)
total_income = 0.0

for uploaded_file in uploaded_files:
    extracted_text = ""
    try:
        pdf_reader = PyPDF2.PdfReader(uploaded_file)
        for page in pdf_reader.pages:
            extracted_text += page.extract_text() or ""

        st.markdown(f"### 📄 {uploaded_file.name}")
        st.text_area("Extracted Text", extracted_text, height=150)

        if extracted_text.strip():
            prompt = f"""
This is a tax-related document. Please do the following:
1. Summarize the document in plain English.
2. Extract the following fields if they exist: Full Name, Social Security Number (SSN), Employer Name, Income Amount, Tax Year.

Document:
{extracted_text[:4000]}
"""
            st.session_state["messages"].append({"role": "user", "content": prompt})
            response = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=st.session_state["messages"]
            )
            reply = response.choices[0].message.content
            st.session_state["messages"].append({"role": "assistant", "content": reply})
            st.markdown("**TaxGPT Summary & Fields:**")
            st.markdown(reply)

            match = re.search(r'(?i)income[^\d\n:\$]*[:\s\$]*([\d,]+\.?\d*)', reply)
            if match:
                income_str = match.group(1).replace(",", "").replace("$", "")
                st.markdown(f"✅ Matched income: ${income_str}")
            if match:
                income_str = match.group(1).replace(",", "").replace("$", "")
                try:
                    total_income += float(income_str)
                except:
                    pass
    except Exception as e:
        st.error(f"Failed to read {uploaded_file.name}: {e}")

if uploaded_files:
    st.markdown(f"### 🧾 Total Income Across All W-2s: **${total_income:,.2f}**")
    tax, breakdown = estimate_tax_with_breakdown(total_income, standard_deduction, filing_status)
    if isinstance(tax, str):
        st.markdown(f"💵 **Estimated Federal Tax Owed:** {tax}")
    else:
        st.markdown(f"💵 **Estimated Federal Tax Owed (after deduction):** ${round(tax, 2)}")
        st.markdown("### 📊 Tax Bracket Breakdown")
        for low, high, rate, amount, owed in breakdown:
            st.markdown(f"- ${low:,}–${high:,} at {int(rate*100)}%: Taxed on ${amount:,.2f} → ${owed:,.2f}")
        pdf_buffer = generate_pdf(filing_status, total_income, standard_deduction, tax, breakdown)
        st.download_button("📥 Download PDF Summary", pdf_buffer, file_name="TaxGPT_TaxSummary.pdf", mime="application/pdf")

user_input = st.text_input("Ask a follow-up tax question:")

if user_input:
    st.session_state["messages"].append({"role": "user", "content": user_input})
    try:
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=st.session_state["messages"]
        )
        reply = response.choices[0].message.content
        st.session_state["messages"].append({"role": "assistant", "content": reply})
        st.markdown(f"**TaxGPT:** {reply}")
    except Exception as e:
        st.error(f"Error: {str(e)}")