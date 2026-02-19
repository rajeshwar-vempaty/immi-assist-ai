"""
Data Ingestion Pipeline — Loads scraped USCIS data into ChromaDB vector store.

Usage:
    cd backend
    python -m scripts.ingest_uscis_data

Steps:
    1. Scrape USCIS data (or load from cached JSON)
    2. Generate embeddings via OpenAI
    3. Store in ChromaDB
"""

import json
import logging
import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


def load_sample_data() -> list[dict]:
    """
    Load sample immigration knowledge for initial testing.
    This provides a working knowledge base before real scraping is set up.
    """
    sample_documents = [
        {
            "content": (
                "H-1B Specialty Occupation Visa Overview: The H-1B visa allows US employers to "
                "temporarily employ foreign workers in specialty occupations. A specialty occupation "
                "requires theoretical and practical application of a body of highly specialized knowledge "
                "and a bachelor's degree or higher in the specific specialty. The initial period of stay "
                "is up to 3 years, extendable to a maximum of 6 years. An employer must file Form I-129, "
                "Petition for a Nonimmigrant Worker, with USCIS on behalf of the worker."
            ),
            "source": "USCIS Policy Manual",
            "section": "H-1B Specialty Occupations",
            "doc_type": "policy",
            "url": "https://www.uscis.gov/working-in-the-united-states/h-1b-specialty-occupations",
        },
        {
            "content": (
                "H-1B Cap and Lottery: Congress has set the H-1B cap at 65,000 per fiscal year, with an "
                "additional 20,000 for beneficiaries with a US master's degree or higher (advanced degree "
                "exemption). Cap-subject petitions must be registered during the annual registration period, "
                "typically in March. If registrations exceed the cap, USCIS conducts a random lottery. "
                "Cap-exempt employers include institutions of higher education, nonprofit research organizations, "
                "and governmental research organizations."
            ),
            "source": "USCIS Policy Manual",
            "section": "H-1B Cap Season",
            "doc_type": "policy",
            "url": "https://www.uscis.gov/working-in-the-united-states/h-1b-specialty-occupations",
        },
        {
            "content": (
                "H-1B Transfer (Portability): Under AC21, an H-1B worker can begin working for a new employer "
                "as soon as the new employer files an H-1B petition (I-129), without waiting for approval. "
                "The worker must have been lawfully admitted, the new petition must be non-frivolous, and the "
                "worker must not have worked without authorization. This is commonly called H-1B transfer or "
                "portability. The new employer must file a new Labor Condition Application (LCA)."
            ),
            "source": "USCIS Policy Manual - AC21",
            "section": "H-1B Portability",
            "doc_type": "policy",
            "url": "https://www.uscis.gov/policy-manual/volume-2-part-h",
        },
        {
            "content": (
                "Form I-140 - Immigrant Petition for Alien Workers: Employers use Form I-140 to petition "
                "for foreign workers under employment-based immigration categories. Categories include: "
                "EB-1 (Priority Workers - extraordinary ability, outstanding professors/researchers, "
                "multinational managers), EB-2 (Advanced Degree Professionals or Exceptional Ability, "
                "including National Interest Waiver), EB-3 (Skilled Workers, Professionals, and Other Workers). "
                "Filing fee varies by category. Premium Processing is available for an additional fee."
            ),
            "source": "USCIS Form Instructions",
            "section": "I-140 Overview",
            "doc_type": "form_instruction",
            "url": "https://www.uscis.gov/i-140",
        },
        {
            "content": (
                "EB-2 National Interest Waiver (NIW): The EB-2 NIW allows foreign nationals to self-petition "
                "without a job offer or labor certification if they can demonstrate that their work is in the "
                "national interest of the United States. Under the Matter of Dhanasar framework, petitioners "
                "must show: (1) the proposed endeavor has substantial merit and national importance, "
                "(2) the petitioner is well-positioned to advance the proposed endeavor, and (3) on balance, "
                "it would be beneficial to the US to waive the job offer and labor certification requirements."
            ),
            "source": "USCIS Policy Manual",
            "section": "EB-2 NIW - Dhanasar Framework",
            "doc_type": "policy",
            "url": "https://www.uscis.gov/policy-manual/volume-6-part-f-chapter-5",
        },
        {
            "content": (
                "Form I-485 - Adjustment of Status: Form I-485 is used by individuals who are already in the "
                "US to apply for lawful permanent resident status (green card). Eligibility generally requires: "
                "an approved or concurrently filed immigrant petition, an immediately available visa number, "
                "physical presence in the US, admissibility. Applicants must submit biometrics, undergo a "
                "medical examination (Form I-693), and may be called for an interview. Filing fees include "
                "the application fee and biometric services fee."
            ),
            "source": "USCIS Form Instructions",
            "section": "I-485 Adjustment of Status",
            "doc_type": "form_instruction",
            "url": "https://www.uscis.gov/i-485",
        },
        {
            "content": (
                "F-1 Optional Practical Training (OPT): F-1 students may apply for OPT to gain practical "
                "training directly related to their field of study. Pre-completion OPT allows part-time work "
                "while enrolled. Post-completion OPT provides up to 12 months of full-time employment after "
                "completing studies. STEM degree holders may apply for a 24-month STEM OPT extension, for a "
                "total of 36 months. Students must file Form I-765 to apply for an Employment Authorization "
                "Document (EAD). The 60-day grace period after OPT ends allows for departure or change of status."
            ),
            "source": "USCIS Policy Manual",
            "section": "F-1 OPT and STEM OPT",
            "doc_type": "policy",
            "url": "https://www.uscis.gov/working-in-the-united-states/students-and-exchange-visitors/optional-practical-training-opt-for-f-1-students",
        },
        {
            "content": (
                "Request for Evidence (RFE) Overview: USCIS issues an RFE when additional evidence is needed "
                "to make a decision on a petition or application. An RFE is not a denial — it's an opportunity "
                "to provide additional documentation. Common RFE reasons include: insufficient evidence of "
                "specialty occupation (H-1B), inadequate proof of qualifications, missing supporting documents, "
                "and questions about the employer-employee relationship. Response deadlines typically range from "
                "30 to 87 days. Failure to respond results in denial based on the existing record."
            ),
            "source": "USCIS Policy Manual",
            "section": "Request for Evidence",
            "doc_type": "policy",
            "url": "https://www.uscis.gov/policy-manual/volume-1-part-e-chapter-6",
        },
        {
            "content": (
                "Green Card through Employment: The employment-based green card process typically involves "
                "three main steps: (1) PERM Labor Certification — employer demonstrates no qualified US workers "
                "available (not required for EB-1 or NIW), (2) I-140 Immigrant Petition — employer or self-petitioner "
                "files with USCIS, (3) I-485 Adjustment of Status or Consular Processing — applicant applies for "
                "permanent residence. Priority dates and visa bulletin cut-off dates determine when each step can "
                "proceed. Wait times vary significantly by country of birth and preference category."
            ),
            "source": "USCIS Policy Manual",
            "section": "Employment-Based Green Card Process",
            "doc_type": "policy",
            "url": "https://www.uscis.gov/green-card/green-card-eligibility/green-card-for-employment-based-immigrants",
        },
        {
            "content": (
                "H-4 EAD (Employment Authorization for H-4 Dependents): Certain H-4 dependent spouses of H-1B "
                "nonimmigrants may be eligible for employment authorization. To qualify, the H-1B principal must "
                "be the beneficiary of an approved I-140 petition, OR must have been granted H-1B status under "
                "sections 106(a) or 104(c) of AC21 (H-1B extensions beyond 6 years). The H-4 spouse files "
                "Form I-765 with supporting documentation. Processing times vary. The H-4 EAD is valid until "
                "the expiration of the H-4 status."
            ),
            "source": "USCIS Policy Manual",
            "section": "H-4 EAD Eligibility",
            "doc_type": "policy",
            "url": "https://www.uscis.gov/working-in-the-united-states/h-4-ead",
        },
        {
            "content": (
                "Premium Processing Service: USCIS offers premium processing for certain form types, guaranteeing "
                "a response within 15 business days (or 45 calendar days for some categories). If USCIS fails to "
                "meet the deadline, it refunds the premium processing fee and continues expedited processing. "
                "A response can be an approval, denial, RFE, or NOID — the guarantee is processing, not approval. "
                "Form I-907 is filed concurrently with or after the underlying petition. Premium processing fees "
                "vary by form type. Available for I-129, I-140, and certain I-539 categories."
            ),
            "source": "USCIS Policy Manual",
            "section": "Premium Processing",
            "doc_type": "policy",
            "url": "https://www.uscis.gov/forms/all-forms/how-do-i-use-premium-processing-service",
        },
        {
            "content": (
                "Visa Bulletin and Priority Dates: The Department of State publishes a monthly Visa Bulletin "
                "showing cutoff dates for each employment-based and family-based preference category by country "
                "of chargeability. If your priority date is before the cutoff date, a visa number is considered "
                "available and you may proceed with adjustment of status or consular processing. Two charts are "
                "published: Final Action Dates and Dates for Filing. USCIS announces monthly which chart to use "
                "for I-485 filing. India and China EB-2 and EB-3 categories typically have the longest waits."
            ),
            "source": "USCIS/DOS",
            "section": "Visa Bulletin",
            "doc_type": "policy",
            "url": "https://travel.state.gov/content/travel/en/legal/visa-law0/visa-bulletin.html",
        },
    ]
    return sample_documents


def ingest_data():
    """Main ingestion pipeline."""
    from app.services.rag_service import get_rag_service

    logger.info("=" * 60)
    logger.info("ImmiAssist AI — Data Ingestion Pipeline")
    logger.info("=" * 60)

    rag = get_rag_service()

    # Check if already populated
    existing_count = rag.policy_collection.count()
    if existing_count > 0:
        logger.info(f"Knowledge base already has {existing_count} documents.")
        response = input("Re-ingest? This will clear existing data. (y/N): ")
        if response.lower() != "y":
            logger.info("Skipping ingestion.")
            return

        # Clear existing
        rag.chroma_client.delete_collection("uscis_policy")
        rag.policy_collection = rag.chroma_client.get_or_create_collection(
            name="uscis_policy",
            metadata={"description": "USCIS Policy Manual, Form Instructions, and Guidance"},
        )
        logger.info("Cleared existing collection.")

    # Load data
    # Try real scraped data first, fall back to samples
    raw_data_path = Path(__file__).parent.parent / "backend" / "data" / "raw" / "uscis_all_documents.json"

    if raw_data_path.exists():
        logger.info("Loading scraped USCIS data...")
        with open(raw_data_path) as f:
            documents = json.load(f)
    else:
        logger.info("No scraped data found. Loading sample knowledge base...")
        documents = load_sample_data()

    logger.info(f"Loaded {len(documents)} documents for ingestion")

    # Prepare for ChromaDB
    texts = [doc["content"] for doc in documents]
    metadatas = [
        {
            "source": doc.get("source", "USCIS"),
            "section": doc.get("section", ""),
            "doc_type": doc.get("doc_type", "policy"),
            "url": doc.get("url", ""),
        }
        for doc in documents
    ]
    ids = [f"doc_{i:04d}" for i in range(len(documents))]

    # Ingest into ChromaDB
    logger.info("Generating embeddings and storing in ChromaDB...")
    rag.add_documents(
        documents=texts,
        metadatas=metadatas,
        ids=ids,
        collection_name="uscis_policy",
    )

    # Verify
    final_count = rag.policy_collection.count()
    logger.info(f"✅ Ingestion complete! Total documents in knowledge base: {final_count}")

    # Test retrieval
    logger.info("\n--- Testing retrieval ---")
    test_queries = [
        "How do I transfer my H1B to a new employer?",
        "What documents do I need for I-485?",
        "What is the EB-2 NIW process?",
    ]
    for query in test_queries:
        results = rag.retrieve(query, n_results=2)
        logger.info(f"\nQuery: {query}")
        for r in results:
            logger.info(f"  → [{r['metadata']['section']}] (distance: {r['distance']:.3f})")


if __name__ == "__main__":
    ingest_data()
