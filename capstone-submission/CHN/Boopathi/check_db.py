import sqlite3

def view_all_records():

    conn = sqlite3.connect("database/cease_requests.db")
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM cease_requests")
    rows = cursor.fetchall()

    if not rows:
        print("No records found in database.")
    else:
        print("\nCease & Desist Records in Database:\n")

        for row in rows:
            print(f"ID: {row[0]}")
            print(f"Date: {row[1]}")
            print(f"Document: {row[2]}")
            print(f"Details: {row[3][:2000]}...")
            print("-" * 50)

    conn.close()


if __name__ == "__main__":
    view_all_records()