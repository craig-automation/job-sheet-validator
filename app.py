import streamlit as st
import pandas as pd
from openai import OpenAI

st.title("Job Sheet Validation Prototype")
st.caption(
    "Prototype tool to reduce invoicing delays caused by missing or incorrect job sheet information"
)

customer_rules = {
    "Customer A": {
        "po_required": True,
        "po_length": 8,
        "valid_contracts": ["Full Service", "Maintenance"],
    },
    "Customer B": {
        "po_required": True,
        "po_length": 10,
        "valid_contracts": ["Repair", "Maintenance"],
    },
    "Customer C": {
        "po_required": False,
        "po_length": None,
        "valid_contracts": ["Full Service", "Repair"],
    },
}

if "job_log" not in st.session_state:
    st.session_state["job_log"] = []


def validate_job_sheet(customer, contract_type, po_number, job_description):
    rules = customer_rules[customer]

    issues = []
    invoice_risk_score = 0

    if rules["po_required"] and not po_number.strip():
        issues.append("Missing PO number for a customer that requires a PO.")
        invoice_risk_score += 3

    if rules["po_required"] and po_number.strip():
        if not po_number.isdigit():
            issues.append("PO number should contain digits only.")
            invoice_risk_score += 2

        if len(po_number) != rules["po_length"]:
            issues.append(f"PO number should be {rules['po_length']} digits for {customer}.")
            invoice_risk_score += 2

    if contract_type not in rules["valid_contracts"]:
        issues.append(f"Contract type '{contract_type}' may not be valid for {customer}.")
        invoice_risk_score += 2

    if not job_description.strip():
        issues.append("Job description / technician notes are missing.")
        invoice_risk_score += 1

    if invoice_risk_score >= 5:
        risk_level = "High"
    elif invoice_risk_score >= 2:
        risk_level = "Medium"
    else:
        risk_level = "Low"

    return issues, invoice_risk_score, risk_level


def analyse_notes_with_ai(customer, contract_type, po_number, job_description, issues, risk_level):
    api_key = st.secrets["OPENAI_API_KEY"]
    client = OpenAI(api_key=api_key)

    prompt = f"""
You are an invoicing risk assistant for an engineering service business.

Analyse the job sheet information and technician notes.
Focus on invoice risk, missing information, PO problems, unclear billing status, and admin follow-up.

Return the output in EXACTLY this format:

AI Risk Summary: <short summary>
Likely Invoice Risk: <Low | Medium | High>
Recommended Action: <specific action>
Reviewer: <Technician | Service Admin | Manager>

Job Details:
Customer: {customer}
Contract Type: {contract_type}
PO Number: {po_number}
Rule-Based Risk Level: {risk_level}
Rule-Based Issues: {issues}
Technician Notes: {job_description}
"""

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": "You are a practical operational improvement assistant."},
            {"role": "user", "content": prompt},
        ],
    )

    return response.choices[0].message.content


def parse_ai_response(text):
    parsed = {}

    fields = [
        "AI Risk Summary",
        "Likely Invoice Risk",
        "Recommended Action",
        "Reviewer",
    ]

    for field in fields:
        if field + ":" in text:
            value = text.split(field + ":")[1]

            for next_field in fields:
                if next_field != field and next_field + ":" in value:
                    value = value.split(next_field + ":")[0]

            parsed[field] = value.strip()

    return parsed


st.subheader("Technician Job Details")

customer = st.selectbox("Customer", list(customer_rules.keys()))

contract_type = st.selectbox(
    "Contract Type",
    ["Full Service", "Maintenance", "Repair", "Unknown"],
)

po_number = st.text_input("Customer PO Number")

job_description = st.text_area("Job Description / Technician Notes")

use_ai = st.checkbox("Include AI analysis of technician notes", value=True)

if st.button("Validate Job Sheet"):
    issues, invoice_risk_score, risk_level = validate_job_sheet(
        customer,
        contract_type,
        po_number,
        job_description,
    )

    st.subheader("Validation Result")

    if issues:
        st.warning("Potential invoicing issues detected")
        for issue in issues:
            st.write(f"- {issue}")
    else:
        st.success("No obvious invoicing issues detected")

    st.subheader("Invoice Risk")

    if risk_level == "High":
        st.error(f"Invoice Risk: {risk_level}")
    elif risk_level == "Medium":
        st.warning(f"Invoice Risk: {risk_level}")
    else:
        st.success(f"Invoice Risk: {risk_level}")

    ai_text = ""
    ai_parsed = {}

    if use_ai:
        try:
            with st.spinner("Running AI note analysis..."):
                ai_text = analyse_notes_with_ai(
                    customer,
                    contract_type,
                    po_number,
                    job_description,
                    issues,
                    risk_level,
                )

            ai_parsed = parse_ai_response(ai_text)

            st.subheader("AI Note Analysis")
            st.write(f"**AI Risk Summary:** {ai_parsed.get('AI Risk Summary', 'Not returned')}")
            st.write(f"**Likely Invoice Risk:** {ai_parsed.get('Likely Invoice Risk', 'Not returned')}")
            st.write(f"**Recommended Action:** {ai_parsed.get('Recommended Action', 'Not returned')}")
            st.write(f"**Reviewer:** {ai_parsed.get('Reviewer', 'Not returned')}")

        except Exception as e:
            st.error(f"AI analysis failed: {e}")

    result = {
        "Customer": customer,
        "Contract Type": contract_type,
        "PO Number": po_number,
        "Rule Issues": len(issues),
        "Rule-Based Risk": risk_level,
        "Risk Score": invoice_risk_score,
        "Issues": "; ".join(issues) if issues else "None",
        "Technician Notes": job_description,
        "AI Risk Summary": ai_parsed.get("AI Risk Summary", ""),
        "AI Invoice Risk": ai_parsed.get("Likely Invoice Risk", ""),
        "AI Recommended Action": ai_parsed.get("Recommended Action", ""),
        "Reviewer": ai_parsed.get("Reviewer", ""),
    }

    st.session_state["job_log"].append(result)

    st.subheader("Job Sheet Summary")
    st.dataframe(pd.DataFrame([result]))

st.subheader("Validation History")

if st.session_state["job_log"]:
    history_df = pd.DataFrame(st.session_state["job_log"])

    risk_order = {
        "High": 3,
        "Medium": 2,
        "Low": 1,
    }

    history_df["Risk Sort"] = history_df["Rule-Based Risk"].map(risk_order).fillna(0)

    history_df = history_df.sort_values(
        by=["Risk Sort", "Risk Score"],
        ascending=False,
    )

    history_df = history_df.drop(columns=["Risk Sort"])

    st.dataframe(history_df)
else:
    st.write("No job sheets validated yet")