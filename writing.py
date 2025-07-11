import streamlit as st
from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

st.set_page_config(page_title="Professional Writing GPT v3", layout="wide")
st.title("📚 Professional Writing GPT (Section-by-Section Mode)")
st.markdown("Generate rich, human-like essays in longform format, section by section.")

# Inputs
topic = st.text_input("Enter your essay topic")
audience = st.selectbox("Target Audience", ["Undergraduate", "Graduate", "Expert"])
length = st.slider("Select essay length (pages)", 2, 20, 10)
citation_style = st.selectbox("Citation Style", ["None", "APA", "MLA", "Chicago"])
use_citations = st.radio("Include citations?", ["Yes (real)", "Yes (placeholder)", "No"])

st.markdown("### ✒️ Select or Customize Your Section Titles")

default_sections = {
    "Introduction": ["Introduction", "Opening Reflections", "Framing the Issue"],
    "Background": ["Historical Context", "Origins of the Debate", "Foundational Perspectives"],
    "Main Argument": ["Theoretical Framework", "Case Analysis", "Critical Evaluation"],
    "Counterargument": ["Alternative Perspectives", "Opposing Theories", "Challenges to Consider"],
    "Conclusion": ["Conclusion", "Implications & Future Research", "Final Thoughts"]
}

section_titles = []
for key, options in default_sections.items():
    col1, col2 = st.columns([2, 3])
    with col1:
        choice = st.selectbox(f"{key} Section", options + ["Custom..."], key=key)
    with col2:
        custom = st.text_input(f"Custom title for {key}", "", key=f"{key}_custom")

    if choice == "Custom..." and custom.strip() != "":
        section_titles.append(custom.strip())
    else:
        section_titles.append(choice)

submit = st.button("Generate Full Essay")

if submit and topic:
    essay_parts = []
    total_words = length * 300
    words_per_section = total_words // len(section_titles)

    with st.spinner("Generating each section..."):
        for section in section_titles:
            section_prompt = f"""
Write a {words_per_section}-word section titled "{section}" for an academic essay on: {topic}.
Target audience: {audience}
Citation style: {citation_style}
Include citations: {use_citations}
Use rich, undetectably human language with deep analysis and transitions. Avoid repetition and shallow summaries.
"""

            messages = [
                {"role": "system", "content": "You are a professional academic writing assistant. Write with deep complexity and avoid sounding like AI."},
                {"role": "user", "content": section_prompt}
            ]

            response = client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                temperature=0.7
            )

            section_text = response.choices[0].message.content
            essay_parts.append(f"## {section}\n\n{section_text}\n")

    final_essay = "\n\n".join(essay_parts)
    st.markdown("### 🧾 Final Essay Output")
    st.write(final_essay)
    st.download_button("📥 Download Full Essay", final_essay, file_name="sectioned_essay.txt")
