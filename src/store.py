import sqlite3

def init_database():
  # Connect to the SQLite database (creates a new file named 'example.db' if it doesn't exist)
  conn = sqlite3.connect('knowledge.db')

  # Create a cursor object to interact with the database
  cursor = conn.cursor()

  # Create a table
  cursor.execute('''CREATE TABLE IF NOT EXISTS knowledge
              (id INTEGER PRIMARY KEY AUTOINCREMENT,
              title TEXT,
              details TEXT)''')
  return conn

def gen_knowledge_summary(conn):
  cursor = conn.cursor()
  cursor.execute("SELECT id,title FROM knowledge")
  return "ID,title\n" + "\n".join((f"{row[0]},{row[1]}" for row in cursor.fetchall()))

def insert_knowledge(conn, title, details):
  cursor = conn.cursor()
  cursor.execute("INSERT INTO knowledge (title, details) VALUES (?, ?)", (title, details))
  conn.commit()
  cursor.close()
  print("knowledge inserted", title, details)

def delete_knowledge(conn, ids):
  if len(ids) == 0:
    return
  cursor = conn.cursor()
  cursor.execute("DELETE from knowledge WHERE id IN (?)", ",".join(ids))
  conn.commit()
  cursor.close()
  print("knowledge deleted", ids)

def restore_knowledge(conn, ids):
  if len(ids) == 0:
    return ""

  ids_str=",".join(map(str, ids))
  cursor = conn.cursor()
  cursor.execute(f"SELECT id,title,details FROM knowledge WHERE id IN ({ids_str})")
  return "\n".join((f"ID:{row[0]} {row[1]}「{row[2]}」" for row in cursor.fetchall()))
