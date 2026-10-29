# LostLink

An AI-powered campus lost-and-found platform that combines rule-based inference, heuristic search, and explainable AI to connect lost items with their owners.

## Overview

LostLink analyses user reports using a forward-chaining inference engine and a heuristic A* search algorithm to identify potential matches between lost and found items. It provides a web-based interface for students to report items and for administrators to verify ownership and manage returns.

The project separates the AI's automated matching (which calculates text similarity, time proximity, and location zones) from the final human verification step, ensuring that no item is returned without an administrator's approval.

## Features

- Rule-Based Inference: Uses a forward-chaining engine with 11 rules to deduce matches based on text, time, location, and category.
- Heuristic Search (A*): Finds the optimal assignment of lost items to found items, exploring fewer nodes than a standard greedy algorithm.
- Explanation Facility: Provides "HOW" (proof trees), "WHY" (one-step justifications), and "WHY NOT" explanations for AI-generated matches.
- Baseline and Evaluation: Includes a built-in benchmark comparing the A* heuristic against a Greedy baseline for precision and efficiency.
- Image Similarity: Compares uploaded photos using a 64-bin colour histogram L1 distance metric.
- Status Tracking: Items transition through states like "Open", "Match Found", "Claim Pending", and "Returned".
- Admin Dashboard: Displays live statistics and allows administrators to approve or reject ownership claims.
- Zero Dependencies: Built entirely using the Python Standard Library. No pip install required.

## Technologies Used

- Python 3 (Standard Library only)
- HTML5, CSS3, Vanilla JavaScript
- JSON (Database persistence)
- HTTP Server (http.server)
- Natural Language Processing (Cosine similarity, synonym mapping)
- Artificial Intelligence (Rule-Based Systems, A* Search)

## Project Structure
```text
lostlink/
├── data/
│   ├── items.json
│   └── claims.json
├── lostlink/
│   ├── __init__.py
│   ├── evaluation.py
│   ├── explanation.py
│   ├── image_sim.py
│   ├── inference.py
│   ├── matching.py
│   ├── models.py
│   ├── nlp.py
│   ├── rules.py
│   ├── search.py
│   ├── seed.py
│   └── store.py
├── static/
│   ├── index.html
│   └── LostLink.html
├── tests/
│   ├── __init__.py
│   └── test_ai.py
├── main.py
├── server.py
└── README.txt
```
## Getting Started

### Prerequisites

- Python 3.10 or newer installed on your system.
- Git (optional, for cloning).
- No pip installations required.

### Installation

Clone the repository (or copy the project folder to your local machine):

git clone https://github.com/harithak157/lostlink.git
cd lostlink

### Run the Application

Start the web server:
```bash
python main.py serve
```
Open the local URL displayed in the terminal (http://127.0.0.1:8000/) to use the application.

To run the AI demonstration in the terminal:
```bash
python main.py demo
```
## Artificial Intelligence Components

The project includes a fully functional AI backend:

- Inference Engine: Applies rules (R1–R11) to derive facts such as likely_match and match_candidate.
- Heuristic Search: A* algorithm minimises the negative confidence score to find the optimal pairing.
- Explainable AI: Generates user-friendly explanations by translating technical proof trees into plain English.

AI predictions are exploratory and should not be treated as definitive proof of ownership. The system requires human administrator verification before an item is returned.

## Data and Limitations

The application relies on a local JSON dataset seeded with 7 demo items. Historical details and user-reported data may be incomplete. Image similarity is currently based on basic colour histograms, which may not recognise complex visual patterns.

Dataset coverage, AI model constraints, and the lack of a persistent relational database should be considered when evaluating the system for large-scale deployment.

## Future Improvements

- Deep learning image matching (CNNs) for visual recognition.
- Database migration to PostgreSQL for scalability.
- Integration with email/SMS APIs for real-time match notifications.
- Multi-campus support with tenant-based isolation.
- Upgraded NLP models (TF-IDF, Word2Vec) for better text understanding.

## Author

[haritha157]
GitHub: [https://github.com/harithak157]
