"""
Data Ingestion Pipeline — Loads USCIS data into ChromaDB vector store.

Usage (from repo root):
    python scripts/ingest_uscis_data.py
    python scripts/ingest_uscis_data.py --yes --collection all
"""

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


def load_sample_data() -> list[dict]:
    """Load sample immigration knowledge for initial testing."""
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
                "H-1B Transfer (Change of Employer): An H-1B worker may begin working for a new employer "
                "upon filing a new I-129 petition with USCIS, under H-1B portability provisions. "
                "The new employer must file Form I-129 before the worker's authorized stay expires. "
                "Required documents include: offer letter, LCA, pay stubs from current employer, "
                "I-94, passport copies, and degree credentials."
            ),
            "source": "USCIS Policy Manual",
            "section": "H-1B Portability",
            "doc_type": "policy",
            "url": "https://www.uscis.gov/working-in-the-united-states/h-1b-specialty-occupations",
        },
        {
            "content": (
                "Form I-485 Adjustment of Status: Form I-485 is used to apply for lawful permanent "
                "resident status (green card) while in the United States. Required documents typically "
                "include: birth certificate, passport photos, I-94, medical examination (I-693), "
                "affidavit of support (I-864) if family-based, employment authorization (I-765) optional, "
                "advance parole (I-131) optional, and filing fee."
            ),
            "source": "USCIS Form Instructions",
            "section": "I-485 Application",
            "doc_type": "form_instructions",
            "url": "https://www.uscis.gov/i-485",
        },
        {
            "content": (
                "EB-2 National Interest Waiver (NIW): The EB-2 NIW allows self-petition without employer "
                "sponsorship if the applicant's work is in the national interest. Criteria include: "
                "advanced degree or exceptional ability, proposed endeavor of substantial merit and "
                "national importance, well-positioned to advance the endeavor, and balance of factors "
                "favors waiving job offer and labor certification requirements (Matter of Dhanasar)."
            ),
            "source": "USCIS Policy Manual",
            "section": "EB-2 NIW",
            "doc_type": "policy",
            "url": "https://www.uscis.gov/working-in-the-united-states/permanent-workers/employment-based-immigration-second-preference-eb-2",
        },
        {
            "content": (
                "F-1 OPT (Optional Practical Training): F-1 students may apply for OPT to work in their "
                "field of study. Standard OPT is 12 months; STEM OPT extension adds 24 months for eligible "
                "STEM degrees. Apply up to 90 days before program end, within 60 days after. File Form I-765 "
                "with fee, photos, I-20 with OPT recommendation, and prior EAD if applicable."
            ),
            "source": "USCIS Policy Manual",
            "section": "F-1 OPT",
            "doc_type": "policy",
            "url": "https://www.uscis.gov/opt",
        },
        {
            "content": (
                "H-1B Lottery (Cap Registration): USCIS conducts an annual lottery for new H-1B cap-subject "
                "petitions. Employers register during the registration period (typically March). Selected "
                "registrations may file I-129 during the filing window. Premium processing available."
            ),
            "source": "USCIS",
            "section": "H-1B Cap",
            "doc_type": "policy",
            "url": "https://www.uscis.gov/working-in-the-united-states/temporary-workers/h-1b-specialty-occupations",
        },
        {
            "content": (
                "Premium Processing: USCIS offers premium processing for certain forms for an additional fee. "
                "USCIS will take action within 15 business days (or issue refund if not). Available for "
                "I-129, I-140, I-539, and others when listed on uscis.gov."
            ),
            "source": "USCIS",
            "section": "Premium Processing",
            "doc_type": "policy",
            "url": "https://www.uscis.gov/forms/explore-my-options/premium-processing",
        },
        {
            "content": (
                "Request for Evidence (RFE): When USCIS needs more information, it issues an RFE. "
                "Respond within the deadline (typically 87 days). Failure to respond may result in denial. "
                "Address each point raised with supporting evidence. RFE responses are critical legal documents."
            ),
            "source": "USCIS Policy Manual",
            "section": "RFE Response",
            "doc_type": "policy",
            "url": "https://www.uscis.gov/policy-manual",
        },
        {
            "content": (
                "L-1 Intracompany Transferee: L-1A for managers/executives, L-1B for specialized knowledge. "
                "Requires one year employment abroad with qualifying organization in past three years. "
                "File Form I-129 with supporting corporate documents."
            ),
            "source": "USCIS Policy Manual",
            "section": "L-1 Visa",
            "doc_type": "policy",
            "url": "https://www.uscis.gov/working-in-the-united-states/temporary-workers/l-1a-intracompany-transferee-executive-or-manager",
        },
        {
            "content": (
                "O-1 Extraordinary Ability: For individuals with extraordinary ability in sciences, arts, "
                "education, business, or athletics. Requires sustained national or international acclaim. "
                "File I-129 with advisory opinion and evidence of awards, publications, judging, etc."
            ),
            "source": "USCIS Policy Manual",
            "section": "O-1 Visa",
            "doc_type": "policy",
            "url": "https://www.uscis.gov/working-in-the-united-states/temporary-workers/o-1-visa-individuals-with-extraordinary-ability-or-achievement",
        },
        {
            "content": (
                "I-140 Immigrant Petition for Alien Workers: Employer or self-petitioner files I-140 for "
                "EB-1, EB-2, or EB-3 categories. Includes evidence of ability to pay, PERM labor "
                "certification (if required), and qualifying credentials."
            ),
            "source": "USCIS Form Instructions",
            "section": "I-140",
            "doc_type": "form_instructions",
            "url": "https://www.uscis.gov/i-140",
        },
        {
            "content": (
                "Visa Bulletin and Priority Dates: The Department of State Visa Bulletin shows when "
                "immigrant visa numbers are available. Priority date must be current for I-485 filing "
                "or consular processing. Categories include EB, F, and family preferences."
            ),
            "source": "Visa Bulletin",
            "section": "Priority Dates",
            "doc_type": "policy",
            "url": "https://travel.state.gov/content/travel/en/legal/visa-law0/visa-bulletin.html",
        },
    ]
    return sample_documents


def load_policy_documents() -> list[dict]:
    raw_data_path = Path(__file__).parent.parent / "backend" / "data" / "raw" / "uscis_all_documents.json"
    if raw_data_path.exists():
        logger.info("Loading scraped USCIS data...")
        with open(raw_data_path) as f:
            return json.load(f)
    logger.info("No scraped data found. Loading sample knowledge base...")
    return load_sample_data()


def load_processing_times_documents() -> list[dict]:
    from data.scrapers.processing_times import get_curated_processing_times

    raw_path = Path(__file__).parent.parent / "backend" / "data" / "raw" / "processing_times.json"
    if raw_path.exists():
        with open(raw_path) as f:
            return json.load(f)
    return get_curated_processing_times()


def record_ingestion_run(collection: str, doc_count: int, status: str) -> None:
    try:
        from app.db.base import SessionLocal
        from app.models.models import IngestionRun

        db = SessionLocal()
        run = IngestionRun(
            collection=collection,
            doc_count=doc_count,
            status=status,
            finished_at=datetime.utcnow() if status in ("completed", "failed") else None,
        )
        db.add(run)
        db.commit()
        db.close()
    except Exception as e:
        logger.warning(f"Could not record ingestion run: {e}")


def ingest_collection(rag, collection_name: str, documents: list[dict], force: bool = False):
    collection = (
        rag.policy_collection
        if collection_name == "uscis_policy"
        else rag.timeline_collection
    )

    existing_count = collection.count()
    if existing_count > 0 and not force:
        logger.info(f"{collection_name} already has {existing_count} documents. Skipping.")
        return existing_count

    if existing_count > 0 and force:
        rag.chroma_client.delete_collection(collection_name)
        if collection_name == "uscis_policy":
            rag.policy_collection = rag.chroma_client.get_or_create_collection(
                name="uscis_policy",
                metadata={"description": "USCIS Policy Manual, Form Instructions, and Guidance"},
            )
        else:
            rag.timeline_collection = rag.chroma_client.get_or_create_collection(
                name="processing_times",
                metadata={"description": "USCIS Processing Times Data"},
            )

    record_ingestion_run(collection_name, 0, "running")

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
    ids = [f"{collection_name}_{i:04d}" for i in range(len(documents))]

    logger.info(f"Ingesting {len(documents)} documents into {collection_name}...")
    rag.add_documents(
        documents=texts,
        metadatas=metadatas,
        ids=ids,
        collection_name=collection_name,
    )

    final = collection.count()
    record_ingestion_run(collection_name, final, "completed")
    logger.info(f"✅ {collection_name}: {final} documents")
    return final


def ingest_data(force: bool = False, collection: str = "all"):
    from app.services.rag_service import get_rag_service

    logger.info("=" * 60)
    logger.info("ImmiAssist AI — Data Ingestion Pipeline")
    logger.info("=" * 60)

    rag = get_rag_service()

    if collection in ("all", "uscis_policy"):
        docs = load_policy_documents()
        ingest_collection(rag, "uscis_policy", docs, force=force)

    if collection in ("all", "processing_times"):
        docs = load_processing_times_documents()
        ingest_collection(rag, "processing_times", docs, force=force)

    logger.info("Ingestion complete.")


def main():
    parser = argparse.ArgumentParser(description="Ingest USCIS data into ChromaDB")
    parser.add_argument(
        "--yes", "-y", action="store_true", help="Force re-ingest (clear existing data)"
    )
    parser.add_argument(
        "--collection",
        choices=["all", "uscis_policy", "processing_times"],
        default="all",
        help="Which collection to ingest",
    )
    args = parser.parse_args()

    if not args.yes:
        from app.services.rag_service import get_rag_service

        rag = get_rag_service()
        if rag.policy_collection.count() > 0:
            logger.info("Knowledge base already populated. Use --yes to force re-ingest.")
            return

    ingest_data(force=args.yes, collection=args.collection)


if __name__ == "__main__":
    main()
