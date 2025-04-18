import streamlit as st
import json
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_community.llms import Ollama
from langchain.prompts import PromptTemplate
from langchain_core.runnables import Runnable
import pdfplumber

class PersonInfo(BaseModel):
    name: str = Field(description="Full name of the person")
    email: str = Field(description="Email address")
    phone: str = Field(description="Phone number")
    education: str = Field(description="Educational background")
    work_experience: str = Field(description="Work experience")
    skills: str = Field(description="List of skills")

parser = PydanticOutputParser(pydantic_object=PersonInfo)

biodata_prompt = PromptTemplate(
    template="""
Extract the following details from the biodata and return it in JSON format:
{format_instructions}

Biodata:
{biodata}
""",
    input_variables=["biodata"],
    partial_variables={"format_instructions": parser.get_format_instructions()},
)

job_review_prompt = PromptTemplate(
    template="""
Given the following biodata and job description, provide the following:
1. A summary of the job description highlighting key responsibilities and required skills.
2. A comparison of the biodata's skills with the job description, indicating any missing skills.
3. How well the biodata aligns with the job description.

Job Description:
{job_description}

Biodata:
{biodata}
""",
    input_variables=["biodata", "job_description"],
)

llm = Ollama(model="mistral")
biodata_chain: Runnable = biodata_prompt | llm | parser
job_review_chain: Runnable = job_review_prompt | llm

st.set_page_config(page_title="Biodata & Job Description Analyzer", layout="centered")
st.title("📄 Biodata & Job Description Analyzer")
st.markdown("Upload a file or paste raw text. The model can extract structured information for form filling and can also compare it with a job description.")

tabs = st.radio("Choose Functionality", ("Form Filler", "Job Description Review"))

if 'biodata_text' not in st.session_state:
    st.session_state.biodata_text = ""
if 'job_description' not in st.session_state:
    st.session_state.job_description = ""

if tabs == "Form Filler":

    st.markdown("Upload a file or paste raw text, and the model will extract structured information from it.")

    uploaded_file = st.file_uploader("Upload File (.pdf or .txt)", type=["pdf", "txt"])
    biodata_text = st.session_state.biodata_text

    if uploaded_file:
        if uploaded_file.type == "application/pdf":
            with pdfplumber.open(uploaded_file) as pdf:
                biodata_text = "\n".join(page.extract_text() for page in pdf.pages if page.extract_text())
        elif uploaded_file.type == "text/plain":
            biodata_text = uploaded_file.read().decode("utf-8")

    manual_input = st.text_area("Or Paste Manually", height=250, value=biodata_text)
    st.session_state.biodata_text = manual_input

    if st.button("🔍 Extract Information"):
        if manual_input.strip() == "":
            st.warning("Please provide input.")
        else:
            with st.spinner("Processing with Mistral ..."):
                try:
                    result: PersonInfo = biodata_chain.invoke({"biodata": manual_input})
                    data = result.dict()
                    st.success("Structured data extracted!")

                    st.markdown("### ✏️ Edit Information Before Using it")
                    name = st.text_input("Name", data["name"])
                    email = st.text_input("Email", data["email"])
                    phone = st.text_input("Phone", data["phone"])
                    education = st.text_area("Education", data["education"])
                    work_experience = st.text_area("Work Experience", data["work_experience"])
                    skills = st.text_area("Skills", data["skills"])

                    final_data = {
                        "name": name,
                        "email": email,
                        "phone": phone,
                        "education": education,
                        "work_experience": work_experience,
                        "skills": skills
                    }

                    st.download_button(
                        label="📥 Download JSON",
                        data=json.dumps(final_data, indent=2),
                        file_name="biodata_info.json",
                        mime="application/json"
                    )

                except Exception as e:
                    st.error(f"Something went wrong: {e}")

elif tabs == "Job Description Review":

    st.markdown("Input the biodata and job description for a detailed review.")
    biodata_for_review = st.text_area("Biodata", height=250, value=st.session_state.biodata_text)
    st.session_state.biodata_text = biodata_for_review
    job_description_input = st.text_area("Paste Job Description (from LinkedIn or any job portal)", height=250, value=st.session_state.job_description)
    st.session_state.job_description = job_description_input

    if st.button("🔍 Analyze Job Description Fit"):
        if biodata_for_review.strip() == "" or job_description_input.strip() == "":
            st.warning("Please provide both biodata and job description input.")
        else:
            with st.spinner("Processing with Mistral ..."):
                try:
                    result = job_review_chain.invoke({
                        "biodata": biodata_for_review, 
                        "job_description": job_description_input
                    })
                    st.success("Analysis Complete!")
                    st.markdown("### 📝 Report:")
                    st.write(result)

                except Exception as e:
                    st.error(f"Something went wrong: {e}")
