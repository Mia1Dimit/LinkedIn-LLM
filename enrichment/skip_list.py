# Skip List: Companies That Should NOT Be Enriched
# 
# These companies are marked as problematic for enrichment and will be skipped
# even if enrichment is requested. They may have:
# - Unclear naming that causes search ambiguity
# - Private/stealth companies with insufficient public data
# - Educational institutions with generic names
# - Archived or inactive companies
#
# Format: Company name (Organization field from COMPANY_FOLLOWS snapshot)
# Last Updated: 2026-05-12
# Start Date Strategy: Only enrich companies followed after 2026-04-16

SKIP_COMPANIES = {
    "Hello SportsTech",
    "Manufact (YC S25)",
    "Clicks",
    "Luiss Guido Carli University",
    "Sapienza Università di Roma",
    "Hinto®Group",
    "skills.lab by Anton Paar",
    "Johan Cruyff Institute",
    "WHU – Otto Beisheim School of Management",
    "Loughborough University London",
    "Finanz - your favourite personal finance app",
    "European University Institute",
    "Dock - Startup Lab",
    "SkillsCloud – ATS per Recruiter",
    "KU Leuven",
    "UNSW",
    "Y Combinator",
    "Fitness Park España",
    "Code Career Mastery",
    "TeamSystem Cybersecurity | Muscope",
    "TrueScreen - Data Authenticity Platform",
    "Visual Studio Code",
    "Trainect AI",
    "Xsens Automation & Mobility",
    "Ghènesis Biotech",
    "EPICODE Institute of Technology",
    "ASTAR | Sport Intelligence",
    "ETH Zürich",
}
