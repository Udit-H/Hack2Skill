# Knowledge Base for Sahayak — Last Mile Justice Navigator

This directory contains curated legal documents, procedures, and practical guides
organized into the following categories:

## Structure

- **bare_acts/** — Key sections of Indian statutes relevant to our 3 crisis tracks
- **procedures/** — Step-by-step procedural guides for courts, police, tribunals
- **resources/** — Emergency contacts, shelter homes, legal aid clinics, government schemes
- **practical/** — Court etiquette, common mistakes, timelines, costs, sample applications

## Ingestion

All `.md` files (except this README) are ingested into ChromaDB via:
```bash
cd backend/playground
python ingest_knowledge_base.py
```

## Crisis Tracks Covered

1. **Eviction / Housing** — Karnataka Rent Act, TPA, injunctions
2. **Domestic Violence** — PWDVA 2005, DV Rules, BNS offences
3. **Senior Citizen Abuse** — Senior Citizens Act 2007, Karnataka rules
4. **Cross-cutting** — Legal aid, evidence, police procedures, helplines
