import sys
from src.auth.auth_utils import hash_password
from src.db import get_db

email = sys.argv[1]
new_password = sys.argv[2]

conn = get_db()
cur = conn.cursor()
cur.execute(
    "UPDATE users SET password_hash = %s WHERE email = %s",
    (hash_password(new_password), email),
)
conn.commit()
print("Updated rows:", cur.rowcount)
cur.close()
conn.close()