from utils.db import get_conn, execute as db_exec
conn = get_conn()
c = db_exec(conn, "SELECT key, value FROM app_settings WHERE key LIKE '%twitter%' OR key LIKE '%twit%' OR key LIKE '%x_api%' OR key LIKE '%bearer%' OR key LIKE '%consumer%'")
rows = c.fetchall()
conn.close()
for k, v in rows:
    print(k, "=", str(v)[:40] if v else "EMPTY")
print("DONE")
