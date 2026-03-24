import sqlite3
from tabulate import tabulate

def visualize_cease_requests(db_path="cease_desist.db"):
    """Prints the cease_requests table in a pretty tabular format."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM cease_requests")
    rows = cursor.fetchall()
    headers = [description[0] for description in cursor.description]
    print(tabulate(rows, headers, tablefmt="grid"))
    conn.close()

if __name__ == "__main__":
    visualize_cease_requests()
