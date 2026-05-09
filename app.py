import streamlit as st
import pandas as pd

st.title("Job Sheet Validation Prototype")
st.caption("Prototype tool to reduce invoicing delays caused by missing or incorrect job sheet information")

customer_rules = {
    "Customer A": {
        "po_required": True,
        "po_length": 8,
        "valid_contracts": ["Full Service", "Maintenance"]
    },
    "Customer B": {
        "po_required": True,
        "po_length": 10,
        "valid_contracts": ["Repair", "Maintenance"]
    },
    "Customer C": {
        "po_required": False,
        "po_length": None,
        "valid_contracts": ["Full Service", "Repair"]
    }
}

st.subheader("Technician Job Details")

customer = st.selectbox("Customer", list(customer_rules.keys()))
contract_type = st.selectbox(
    "Contract Type",
    ["Full Service", "Maintenance", "Repair", "Unknown"]
)

po_number = st.text_input("Customer PO Number")
job_description = st.text_area("Job Description / Technician Notes")

if st.button("Validate Job Sheet"):
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
            issues.append(
                f"PO number should be {rules['po_length']} digits for {customer}."
            )
            invoice_risk_score += 2

    if contract_type not in rules["valid_contracts"]:
        issues.append(
            f"Contract type '{contract_type}' may not be valid for {customer}."
        )
        invoice_risk_score += 2

    if not job_description.strip():
        issues.append("Job description / technician notes are missing.")
        invoice_risk_score += 1

    st.subheader("Validation Result")

    if issues:
        st.warning("Potential invoicing issues detected")

        for issue in issues:
            st.write(f"- {issue}")
    else:
        st.success("No obvious invoicing issues detected")

    st.subheader("Invoice Risk")

    if invoice_risk_score >= 5:
        risk_level = "High"
        st.error(f"Invoice Risk: {risk_level}")
    elif invoice_risk_score >= 2:
        risk_level = "Medium"
        st.warning(f"Invoice Risk: {risk_level}")
    else:
        risk_level = "Low"
        st.success(f"Invoice Risk: {risk_level}")

    result = {
        "Customer": customer,
        "Contract Type": contract_type,
        "PO Number": po_number,
        "Invoice Risk": risk_level,
        "Risk Score": invoice_risk_score,
        "Issues Found": len(issues)
    }

    st.subheader("Job Sheet Summary")
    st.dataframe(pd.DataFrame([result]))