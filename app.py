import sqlite3
import re
from datetime import date

import pandas as pd
import streamlit as st
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

connection = sqlite3.connect("applications.db")

connection.execute("""
    CREATE TABLE IF NOT EXISTS applications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company TEXT NOT NULL,
        role TEXT NOT NULL,
        status TEXT NOT NULL
    )
""")

try:
    connection.execute(
        "ALTER TABLE applications ADD COLUMN stipend TEXT"
    )
except sqlite3.OperationalError:
    pass

connection.commit()
try:
    connection.execute(
        "ALTER TABLE applications ADD COLUMN deadline TEXT"
    )
except sqlite3.OperationalError:
    pass

try:
    connection.execute(
        "ALTER TABLE applications ADD COLUMN job_link TEXT"
    )
except sqlite3.OperationalError:
    pass

connection.commit()
connection.close()

st.set_page_config(page_title="ApplyTrack")

st.title("ApplyTrack")
st.write("My internship application tracker")

st.subheader("Add an internship application")

company = st.text_input("Company name")
role = st.text_input("Role")

status = st.selectbox(
    "Application status",
    ["Saved", "Applied", "Interview", "Rejected"]
)

stipend = st.text_input("Monthly stipend", placeholder="e.g. ₹15,000")
   
deadline = st.text_input(
    "Application deadline",
    placeholder="e.g. 2026-09-15"
)

job_link = st.text_input(
    "Job link",
    placeholder="https://company.com/internship"
)

if st.button("Save application"):
    if company.strip() == "" or role.strip() == "":
        st.warning("Company name and role are required.")
    else:
        with sqlite3.connect("applications.db") as connection:
            connection.execute(
                """
                INSERT INTO applications (company, role, status, stipend, deadline, job_link)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (company, role, status, stipend, deadline, job_link)
            )

        st.success("Application saved successfully!")

with sqlite3.connect("applications.db") as connection:
    applications = pd.read_sql_query(
        "SELECT id, company, role, status, stipend, deadline, job_link FROM applications ORDER BY id DESC",
        connection
    )

    today = date.today().isoformat()

upcoming_deadlines = applications[
    (applications["deadline"] != "") &
    (applications["deadline"] >= today)
].sort_values("deadline").head(5)

st.subheader("Upcoming deadlines")

if upcoming_deadlines.empty:
    st.info("No upcoming deadlines.")
else:
    st.dataframe(
        upcoming_deadlines[
            ["company", "role", "deadline", "status", "job_link"]
        ],
        use_container_width=True
    )
    csv_data = applications.to_csv(index=False).encode("utf-8")

st.download_button(
    label="Download applications as CSV",
    data=csv_data,
    file_name="my-internship-applications.csv",
    mime="text/csv"
)

total_applications = len(applications)
applied_count = (applications["status"] == "Applied").sum()
interview_count = (applications["status"] == "Interview").sum()
rejected_count = (applications["status"] == "Rejected").sum()

col1, col2, col3, col4 = st.columns(4)

col1.metric("Total", total_applications)
col2.metric("Applied", applied_count)
col3.metric("Interviews", interview_count)
col4.metric("Rejected", rejected_count)

st.subheader("Saved applications")
if applications.empty:
    st.info("No applications saved yet.")
else:
    filter_status = st.selectbox(
        "Filter applications by status",
        ["All", "Saved", "Applied", "Interview", "Rejected"]
    )

    if filter_status == "All":
        filtered_applications = applications
    else:
        filtered_applications = applications[
            applications["status"] == filter_status
        ]

    st.dataframe(
    filtered_applications,
    use_container_width=True,
    column_config={
        "job_link": st.column_config.LinkColumn("Job link")
    }
)
    st.subheader("Update application status")

    selected_id = st.selectbox(
        "Select application ID",
        applications["id"].tolist()
    )

    new_status = st.selectbox(
        "New status",
        ["Saved", "Applied", "Interview", "Rejected"]
    )

    if st.button("Update status"):
        with sqlite3.connect("applications.db") as connection:
            connection.execute(
                """
                UPDATE applications
                SET status = ?
                WHERE id = ?
                """,
                (new_status, selected_id)
            )

        st.success("Status updated successfully!")
        st.rerun()
        st.subheader("Resume–Job Description Matcher")

resume_text = st.text_area(
    "Paste your resume text",
    height=200
)

job_description = st.text_area(
    "Paste the job description",
    height=200
)

if st.button("Calculate match score"):
    if resume_text.strip() == "" or job_description.strip() == "":
        st.warning("Please paste both resume and job description.")
    else:
        vectorizer = TfidfVectorizer(stop_words="english")

        text_matrix = vectorizer.fit_transform(
            [resume_text, job_description]
        )

        similarity_score = cosine_similarity(
            text_matrix[0:1],
            text_matrix[1:2]
        )[0][0]

        match_percentage = similarity_score * 100

        st.metric(
            "Resume match score",
            f"{match_percentage:.1f}%"
        )
        if match_percentage >= 70:
            st.success("Strong match! You can apply confidently.")
        elif match_percentage >= 40:
            st.warning("Moderate match. Consider improving your resume keywords.")
        else:
            st.error("Low match. Add more relevant skills from the job description.")
            stop_words = {
    "the", "and", "for", "with", "from",
    "this", "that", "you", "are", "your",
    "our", "into", "will", "have", "has",
    "looking"
}

resume_words = set(
    re.findall(r"[a-zA-Z][a-zA-Z+#.-]*", resume_text.lower())
)

job_words = set(
    re.findall(r"[a-zA-Z][a-zA-Z+#.-]*", job_description.lower())
)
stop_words = {
    "the", "and", "for", "with", "from",
    "this", "that", "you", "are", "your",
    "our", "into", "will", "have", "has",
    "looking"
}

job_words = job_words - stop_words

matched_keywords = sorted(resume_words.intersection(job_words))
missing_keywords = sorted(job_words - resume_words)

st.write(
    "Matched keywords:",
    ", ".join(matched_keywords) if matched_keywords else "None"
)

st.write(
    "Potential missing keywords:",
    ", ".join(missing_keywords) if missing_keywords else "None"
)