from src.db import get_db

def get_all_specializations():
    conn = get_db()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT DISTINCT specialization FROM doctors")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [r["specialization"] for r in rows]

def get_doctors_by_specialization(specialization: str):
    conn = get_db()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM doctors WHERE specialization = %s", (specialization,))
    doctors = cur.fetchall()
    cur.close()
    conn.close()
    return doctors

def get_available_slots(doctor_id: int):
    conn = get_db()
    cur = conn.cursor(dictionary=True)
    cur.execute(
        "SELECT * FROM doctor_slots WHERE doctor_id = %s AND is_booked = FALSE ORDER BY slot_date, slot_time",
        (doctor_id,)
    )
    slots = cur.fetchall()
    cur.close()
    conn.close()
    return slots

def book_slot(user_id: int, doctor_id: int, slot_id: int, reason: str):
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("SELECT is_booked FROM doctor_slots WHERE id = %s FOR UPDATE", (slot_id,))
        row = cur.fetchone()
        if not row or row[0]:
            return False  # already booked or doesn't exist

        cur.execute("UPDATE doctor_slots SET is_booked = TRUE WHERE id = %s", (slot_id,))
        cur.execute(
            "INSERT INTO appointments (user_id, doctor_id, slot_id, reason) VALUES (%s, %s, %s, %s)",
            (user_id, doctor_id, slot_id, reason)
        )
        conn.commit()
        return True
    finally:
        cur.close()
        conn.close()

def get_user_appointments(user_id: int):
    conn = get_db()
    cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT a.id, a.reason, a.status, d.name AS doctor_name, d.specialization,
               s.slot_date, s.slot_time
        FROM appointments a
        JOIN doctors d ON a.doctor_id = d.id
        JOIN doctor_slots s ON a.slot_id = s.id
        WHERE a.user_id = %s
        ORDER BY s.slot_date, s.slot_time
    """, (user_id,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

def get_patient_context_summary(user_id: int) -> str | None:
    appointments = get_user_appointments(user_id)
    if not appointments:
        return None

    lines = []
    for a in appointments[-5:]:  # last 5 visits max
        lines.append(
            f"- Visited {a['doctor_name']} ({a['specialization']}) on {a['slot_date']}"
            f"{', reason: ' + a['reason'] if a['reason'] else ''} — status: {a['status']}"
        )
    return "This patient's past appointments:\n" + "\n".join(lines)

def add_doctor(name: str, specialization: str):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("INSERT INTO doctors (name, specialization) VALUES (%s, %s)", (name, specialization))
    conn.commit()
    cur.close()
    conn.close()

def get_all_doctors():
    conn = get_db()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM doctors ORDER BY specialization, name")
    doctors = cur.fetchall()
    cur.close()
    conn.close()
    return doctors

def add_slot(doctor_id: int, slot_date: str, slot_time: str):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO doctor_slots (doctor_id, slot_date, slot_time) VALUES (%s, %s, %s)",
        (doctor_id, slot_date, slot_time)
    )
    conn.commit()
    cur.close()
    conn.close()

def get_all_slots():
    conn = get_db()
    cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT s.id, d.name AS doctor_name, s.slot_date, s.slot_time, s.is_booked
        FROM doctor_slots s
        JOIN doctors d ON s.doctor_id = d.id
        ORDER BY s.slot_date, s.slot_time
    """)
    slots = cur.fetchall()
    cur.close()
    conn.close()
    return slots

def delete_doctor(doctor_id: int):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM doctors WHERE id = %s", (doctor_id,))
    conn.commit()
    cur.close()
    conn.close()