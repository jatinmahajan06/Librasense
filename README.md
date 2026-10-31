# LIBRASENSE — Library Book Usage & Demand Analysis

A runnable academic mini-project built with Python, Flask, pandas and NumPy. The interface includes a librarian dashboard and a student book finder.

## Features
- Librarian dashboard: total titles/copies, available copies, low-stock alerts, category borrowing chart, automatic rule-based insights.
- Most borrowed and underutilised books.
- Demand score (0–100) based on borrowing, scarcity and rating.
- Purchase recommendations: High priority / Consider buying / Monitor.
- Dataset upload from CSV and export of the active data.
- Student search by title, author, category or ID; category filters; availability, rating and expected return information.
- Demo borrow/return actions update the local CSV data.
- Responsive layout for laptop and mobile.

## Run locally
Recommended: Python 3.10+.

```bash
cd LIBRASENSE
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:5000

On first run, `data/library_books.csv` is created with fictional demonstration records.

## CSV columns
Required columns:
`book_id,title,author,category,total_copies,available_copies,borrow_count,rating,return_days`

- `total_copies`: total number of copies in the collection
- `available_copies`: copies available now (must not exceed total copies)
- `borrow_count`: historical borrowing count
- `rating`: score from 0 to 5
- `return_days`: approximate days until the next expected return; use 0 when unknown

The importer also accepts common aliases like `book_title`, `name`, `copies`, `available`, `loans`, and `avg_rating`.

## Project notes / limitations
- The included dataset is fictional sample data; replace it with a real, appropriately licensed dataset or library records.
- This is a mini-project demo, not a production library system. Librarian/student roles are UI modes only, not secure accounts. Do not use it for real student data until authentication, role-based permissions, CSRF protection, backups, and proper circulation/loan records are implemented.
- Ratings and expected return dates are only as accurate as the data supplied. The current app stores expected return as an approximate day count, not an individual borrower-level due date.
- Insights and demand scores are transparent heuristic analytics, not a trained AI model.
- Matplotlib and seaborn are listed as project dependencies for future analysis/report plots; the current dashboard charts are rendered in the browser.
