from sqlalchemy import create_engine, text
from config import LOGS_DB_CONFIG

# =========================
# SQL Server Engine
# =========================
connection_string = (
    f"mssql+pyodbc://{LOGS_DB_CONFIG['username']}:{LOGS_DB_CONFIG['password']}@"
    f"{LOGS_DB_CONFIG['server']}/{LOGS_DB_CONFIG['database']}"
    f"?driver={LOGS_DB_CONFIG['driver']}&TrustServerCertificate=yes"
)

engine = create_engine(
    connection_string,
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
    pool_pre_ping=True
)

# =========================
# LOG SIM LIBERATION
# =========================
def log_sim_liberation(
    action_type: str,
    status: int,                # 1 = success / 0 = error
    created_by: str,
    user_type: str = None,      # 👈 NOUVELLE COLONNE
    num_sim: str = None,
    sim_status: str = None,
    dealer_id: int = None,
    message: str = None,
    ip_address: str = None
):
    """
    Insert log into SimLiberationProdUat table
    """

    query = text("""
        INSERT INTO SimLiberationProdUat
        (
            action_type,
            status,
            created_at,
            created_by,
            user_type,
            num_sim,
            sim_status,
            dealer_id,
            message,
            ip_address
        )
        VALUES
        (
            :action_type,
            :status,
            GETDATE(),
            :created_by,
            :user_type,
            :num_sim,
            :sim_status,
            :dealer_id,
            :message,
            :ip_address
        )
    """)

    data = {
        "action_type": action_type,
        "status": int(status),                       # sécurise BIT
        "created_by": created_by.lower() if created_by else None,
        "user_type": user_type,                      # 👈 NOUVEAU
        "num_sim": num_sim,
        "sim_status": sim_status,
        "dealer_id": dealer_id,
        "message": message,
        "ip_address": ip_address
    }

    try:
        with engine.connect() as connection:
            connection.execute(query, data)
            connection.commit()
    except Exception as e:
        print(f"[LOG ERROR] Failed to insert SimLiberationProdUat entry: {e}")
