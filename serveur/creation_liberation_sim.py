import io
import re
import cx_Oracle
import paramiko
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
import traceback
import os
from dotenv import load_dotenv
from logs import log_sim_liberation

# === Charger variables d'environnement ===
load_dotenv()

# === CONFIG DB / SFTP depuis .env ===
# PROD
DB_HOST_PROD = os.getenv("DB_HOST_PROD")
DB_PORT_PROD = int(os.getenv("DB_PORT_PROD", "1521"))
DB_SERVICE_PROD = os.getenv("DB_SERVICE_PROD")
DB_USER_PROD = os.getenv("DB_USER_PROD")
DB_PASSWORD_PROD = os.getenv("DB_PASSWORD_PROD")

# UAT
DB_HOST_UAT = os.getenv("DB_HOST_UAT")
DB_PORT_UAT = int(os.getenv("DB_PORT_UAT", "1521"))
DB_SERVICE_UAT = os.getenv("DB_SERVICE_UAT")
DB_USER_UAT = os.getenv("DB_USER_UAT")
DB_PASSWORD_UAT = os.getenv("DB_PASSWORD_UAT")

# SFTP
SFTP_HOST = os.getenv("SFTP_HOST")
SFTP_PORT = int(os.getenv("SFTP_PORT", "22"))
SFTP_USER = os.getenv("SFTP_USER")
SFTP_PASSWORD = os.getenv("SFTP_PASSWORD")
SFTP_INBOX_DIR = os.getenv("SFTP_INBOX_DIR")

# SIM config
PREFIX = os.getenv("SIM_PREFIX", "8921303")
SUFFIX = os.getenv("SIM_SUFFIX", "F")

# =========================
# Connexion Oracle helpers
# =========================
def get_connection(env) -> Tuple[cx_Oracle.Connection, cx_Oracle.Cursor]:
    if env.upper() == "PROD":
        host, port, service, user, pwd = DB_HOST_PROD, DB_PORT_PROD, DB_SERVICE_PROD, DB_USER_PROD, DB_PASSWORD_PROD
    else:
        host, port, service, user, pwd = DB_HOST_UAT, DB_PORT_UAT, DB_SERVICE_UAT, DB_USER_UAT, DB_PASSWORD_UAT
    dsn = cx_Oracle.makedsn(host, port, service_name=service)
    conn = cx_Oracle.connect(user=user, password=pwd, dsn=dsn)
    return conn, conn.cursor()

def close_connection(conn: Optional[cx_Oracle.Connection], cur: Optional[cx_Oracle.Cursor]) -> None:
    try:
        if cur:
            cur.close()
    finally:
        if conn:
            conn.close()

# =========================
# Normalisation & validation
# =========================
def normalize_iccid(iccid: str) -> str:
    iccid = iccid.strip()
    if len(iccid) == 12 and iccid.isdigit():
        return f"{PREFIX}{iccid}{SUFFIX}"
    return iccid

def is_valid_sm_serialnum(sm_serialnum: str) -> bool:
    return re.match(rf'^{PREFIX}\d{{12}}{SUFFIX}$', (sm_serialnum or "").strip().upper()) is not None

# =========================
# SPML building & SFTP upload
# =========================
def _build_auc_spml(cursor: cx_Oracle.Cursor, sims: List[str]) -> io.BytesIO:
    root = ET.Element('spml:batchRequest', {
        'language': 'en_us',
        'execution': 'synchronous',
        'processing': 'parallel',
        'xmlns:spml': 'urn:siemens:names:prov:gw:SPML:2:0',
        'xmlns:subscriber': 'urn:siemens:names:prov:gw:SUBSCRIBER:1:0',
        'xmlns:xsi': 'http://www.w3.org/2001/XMLSchema-instance',
        'onError': 'resume'
    })
    version = ET.SubElement(root, 'version')
    version.text = 'SUBSCRIBER_v10'

    sql = """
        SELECT p.port_num, p.port_ki, p.port_tkey,
               DECODE(sm.smc_id, 3, 1, 0) AS algoId,
               DECODE(sm.smc_id, 3, 2, 1) AS acsub
        FROM port p, storage_medium sm
        WHERE sm_serialnum = :sm_serialnum
          AND p.sm_id = sm.sm_id
    """

    for sm_serialnum in sims:
        cursor.execute(sql, sm_serialnum=sm_serialnum)
        rows = cursor.fetchall()
        if not rows:
            continue
        for port_num, port_ki, port_tkey, algoId, acsub in rows:
            request = ET.SubElement(root, 'request', {'xsi:type': 'spml:AddRequest'})
            ET.SubElement(request, 'version').text = 'SUBSCRIBER_v10'
            obj = ET.SubElement(request, 'object', {'xsi:type': 'subscriber:Subscriber'})
            ET.SubElement(obj, 'identifier').text = port_num
            auc = ET.SubElement(obj, 'auc')
            ET.SubElement(auc, 'imsi').text = port_num
            ET.SubElement(auc, 'encKey').text = port_ki
            ET.SubElement(auc, 'algoId').text = str(algoId)
            ET.SubElement(auc, 'kdbId').text = '1' + port_tkey[-2:]
            ET.SubElement(auc, 'acsub').text = str(acsub)

    byte_stream = io.BytesIO()
    ET.ElementTree(root).write(byte_stream, encoding='utf-8', xml_declaration=True)
    byte_stream.seek(0)
    return byte_stream

def _sftp_upload(fileobj: io.BytesIO) -> str:
    transport = paramiko.Transport((SFTP_HOST, SFTP_PORT))
    transport.connect(username=SFTP_USER, password=SFTP_PASSWORD)
    sftp = paramiko.SFTPClient.from_transport(transport)
    current_time = datetime.now().strftime("%d%m%Y_%H%M%S")
    auc_filename = f'auc{SFTP_USER}{current_time}.SPML'
    remote_path = f'{SFTP_INBOX_DIR}/{auc_filename}'
    try:
        sftp.putfo(fileobj, remote_path)
        return auc_filename
    finally:
        sftp.close()
        transport.close()

# =========================
# création AUC
# =========================
def creationauc(sims: List[str], env: str = "PROD", is_file: bool = False) -> Dict[str, Any]:
    conn, cursor = None, None
    out = {"success": False, "processed": [], "skipped": [], "message": ""}

    try:
        sims_norm = [normalize_iccid(s) for s in sims]
        valid = [s for s in sims_norm if is_valid_sm_serialnum(s)]
        skipped = [orig for orig, norm in zip(sims, sims_norm) if not is_valid_sm_serialnum(norm)]
        out["skipped"] = skipped

        if not valid:
            out["message"] = "Aucun ICCID valide."
            return out

        conn, cursor = get_connection(env)

        spml = _build_auc_spml(cursor, valid)

        if spml.getbuffer().nbytes <= 60:
            out["message"] = f"Aucune donnée AUC trouvée en {env}."
            return out

        filename = _sftp_upload(spml)

        out.update({
            "success": True,
            "processed": valid,
            "filename": filename,
            "message": f"AUC créé avec succès en {env} ({filename})"
        })
        return out

    except Exception as e:
        out["message"] = f"Erreur création AUC ({env}): {str(e)}"
        return out

    finally:
        close_connection(conn, cursor)



# =========================
# Liberate fusionné PROD/UAT
# =========================



def liberate_prod(user_inputs: List[str], username: str, user_type: str, ip_address: str, is_file=False) -> Dict[str, Any]:
    status_list = []
    conn, cursor = get_connection("PROD")

    try:
        for raw in user_inputs:
            sim = normalize_iccid(raw.strip())

            # Validation SIM
            if not is_valid_sm_serialnum(sim):
                msg = "Invalid SIM number"
                status_list.append({"sim": raw, "status": "error", "message": msg})
                log_sim_liberation(
                    action_type="PROD",
                    status=0,
                    created_by=username,
                    user_type=user_type,
                    num_sim=sim,
                    sim_status=None,
                    dealer_id=None,
                    message=msg,
                    ip_address=ip_address
                )
                continue

            # Recherche SIM PROD
            cursor.execute("""
                SELECT sm_status, dealer_id
                FROM storage_medium
                WHERE sm_serialnum = :sim
            """, sim=sim)
            row = cursor.fetchone()

            if not row:
                msg = "SIM not found in PROD"
                status_list.append({"sim": raw, "status": "not_found", "message": msg})
                log_sim_liberation(
                    action_type="PROD",
                    status=0,
                    created_by=username,
                    user_type=user_type,
                    num_sim=sim,
                    sim_status=None,
                    dealer_id=None,
                    message=msg,
                    ip_address=ip_address
                )
                continue

            sm_status, dealer_id = row

            # --- Cas déjà libre ---
            if sm_status == 'r' and dealer_id == 31970747:
                # Vérification port
                cursor.execute("""
                    SELECT port_status, dealer_id
                    FROM port
                    WHERE sm_id = (
                        SELECT sm_id FROM storage_medium WHERE sm_serialnum = :sim
                    )
                """, sim=sim)
                row_port = cursor.fetchone()

                if row_port:
                    port_status, port_dealer = row_port
                    # Update port si nécessaire
                    if not (port_status == 'r' and port_dealer == 31970747):
                        cursor.execute("""
                            UPDATE port
                            SET port_status='r',
                                dealer_id=31970747,
                                port_statusmoddat=SYSDATE,
                                port_moddate=SYSDATE,
                                dn_id=NULL,
                                BUSINESS_UNIT_ID=2
                            WHERE sm_id = (
                                SELECT sm_id FROM storage_medium WHERE sm_serialnum=:sim
                            )
                        """, sim=sim)
                        conn.commit()

                # Message fixe
                msg = "Already free in PROD"
                status = 1

                # Créer AUC quand même (optionnel, on ignore le résultat pour le message)
                _ = creationauc([raw], env="PROD", is_file=is_file)

            # Cas à libérer
            elif sm_status in ['d'] or (sm_status == 'r' and dealer_id is None):
                # Liberate + AUC
                cursor.execute("""
                    UPDATE storage_medium
                    SET sm_status='r',
                        dealer_id=31970747,
                        sm_status_mod_date=SYSDATE,
                        sm_delivery_id=31970747,
                        rec_version=2,
                        prepaid_profile_id=NULL,
                        BUSINESS_UNIT_ID=2
                    WHERE sm_serialnum=:sim
                """, sim=sim)

                cursor.execute("""
                    UPDATE port
                    SET port_status='r',
                        dealer_id=31970747,
                        port_statusmoddat=SYSDATE,
                        port_moddate=SYSDATE,
                        dn_id=NULL,
                        BUSINESS_UNIT_ID=2
                    WHERE sm_id = (
                        SELECT sm_id FROM storage_medium WHERE sm_serialnum=:sim
                    )
                """, sim=sim)
                conn.commit()

                auc = creationauc([raw], env="PROD", is_file=is_file)
                msg = "SIM liberated & AUC created in PROD" if auc.get("success") else auc.get("message")
                status = 1 if auc.get("success") else 0

            # Cas SIM active
            elif sm_status == 'a':
                msg = "Already active in PROD"
                status = 0

            # Cas SIM bloquée
            elif sm_status == 'b':
                msg = "SIM blocked in PROD"
                status = 0

            else:
                msg = "Statut inconnu PROD"
                status = 0

            # Ajout à la liste et log
            status_list.append({"sim": raw, "status": "success" if status == 1 else "error", "message": msg})

            log_sim_liberation(
                action_type="PROD",
                status=status,
                created_by=username,
                user_type=user_type,
                num_sim=sim,
                sim_status=sm_status,
                dealer_id=dealer_id,
                message=msg,
                ip_address=ip_address
            )

        return {"success": True, "statusList": status_list}

    finally:
        close_connection(conn, cursor)



def liberate_uat(user_inputs: List[str], username: str, user_type: str, ip_address: str, is_file=False) -> Dict[str, Any]:
    status_list = []
    conn_uat, cursor_uat = get_connection("UAT")
    conn_prod, cursor_prod = get_connection("PROD")

    try:
        for raw in user_inputs:
            sim = normalize_iccid(raw.strip())

            # Validation SIM
            if not is_valid_sm_serialnum(sim):
                msg = "Invalid SIM number"
                status_list.append({"sim": raw, "status": "error", "message": msg})
                log_sim_liberation(
                    action_type="UAT",
                    status=0,
                    created_by=username,
                    user_type=user_type,
                    num_sim=sim,
                    sim_status=None,
                    dealer_id=None,
                    message=msg,
                    ip_address=ip_address
                )
                continue

            # Vérification PROD
            cursor_prod.execute(
                "SELECT sm_status FROM storage_medium WHERE sm_serialnum=:sim",
                sim=sim
            )
            row_prod = cursor_prod.fetchone()
            if row_prod and row_prod[0] == 'a':
                msg = "Already active in PROD"
                status_list.append({"sim": raw, "status": "error", "message": msg})
                log_sim_liberation(
                    action_type="UAT",
                    status=0,
                    created_by=username,
                    user_type=user_type,
                    num_sim=sim,
                    sim_status='a',
                    dealer_id=None,
                    message=msg,
                    ip_address=ip_address
                )
                continue

            # Recherche UAT
            cursor_uat.execute("""
                SELECT sm_status, dealer_id
                FROM storage_medium
                WHERE sm_serialnum=:sim
            """, sim=sim)
            row = cursor_uat.fetchone()

            if row:
                sm_status, dealer_id = row

                # --- Cas déjà libre ---
                if sm_status == 'r' and dealer_id == 31970747:
                    # Vérification port
                    cursor_uat.execute("""
                        SELECT port_status, dealer_id
                        FROM port
                        WHERE sm_id = (
                            SELECT sm_id FROM storage_medium WHERE sm_serialnum = :sim
                        )
                    """, sim=sim)
                    row_port = cursor_uat.fetchone()

                    if row_port:
                        port_status, port_dealer = row_port
                        # Update port si nécessaire
                        if not (port_status == 'r' and port_dealer == 31970747):
                            cursor_uat.execute("""
                                UPDATE port
                                SET port_status='r',
                                    dealer_id=31970747,
                                    port_statusmoddat=SYSDATE,
                                    port_moddate=SYSDATE,
                                    dn_id=NULL,
                                    BUSINESS_UNIT_ID=2
                                WHERE sm_id = (
                                    SELECT sm_id FROM storage_medium WHERE sm_serialnum=:sim
                                )
                            """, sim=sim)
                            conn_uat.commit()

                    # Message fixe
                    msg = "Already free in UAT"
                    status = 1

                    # Créer AUC quand même (optionnel)
                    _ = creationauc([raw], env="UAT", is_file=is_file)

                # Cas SIM active
                elif sm_status == 'a':
                    msg = "Already active in UAT"
                    status = 0

                # UPDATE libération
                elif sm_status in ['d'] or (sm_status == 'r' and dealer_id is None):
                    cursor_uat.execute("""
                        UPDATE storage_medium
                        SET sm_status='r',
                            dealer_id=31970747,
                            sm_status_mod_date=SYSDATE,
                            sm_delivery_id=31970747,
                            rec_version=2,
                            prepaid_profile_id=NULL,
                            BUSINESS_UNIT_ID=2
                        WHERE sm_serialnum=:sim
                    """, sim=sim)

                    cursor_uat.execute("""
                        UPDATE port
                        SET port_status='r',
                            dealer_id=31970747,
                            port_statusmoddat=SYSDATE,
                            port_moddate=SYSDATE,
                            dn_id=NULL,
                            BUSINESS_UNIT_ID=2
                        WHERE sm_id = (
                            SELECT sm_id FROM storage_medium WHERE sm_serialnum=:sim
                        )
                    """, sim=sim)
                    conn_uat.commit()

                    auc = creationauc([raw], env="UAT", is_file=is_file)
                    msg = "SIM liberated & AUC created in UAT" if auc.get("success") else auc.get("message")
                    status = 1 if auc.get("success") else 0

                # 🔴 Cas p → SIM_TO_UPDATE
                elif sm_status == 'p':
                    cursor_uat.execute(
                        "INSERT INTO MEDIATION.SIM_TO_UPDATE VALUES (:sim, NULL, NULL)",
                        sim=sim
                    )
                    cursor_uat.execute("CALL MEDIATION.UPDATE_SIM_TEST()")
                    conn_uat.commit()

                    auc = creationauc([raw], env="UAT", is_file=is_file)
                    msg = "SIM updated & AUC created in UAT" if auc.get("success") else auc.get("message")
                    status = 1 if auc.get("success") else 0

                else:
                    msg = "Unknown UAT status"
                    status = 0

                log_sim_liberation(
                    action_type="UAT",
                    status=status,
                    created_by=username,
                    user_type=user_type,
                    num_sim=sim,
                    sim_status=sm_status,
                    dealer_id=dealer_id,
                    message=msg,
                    ip_address=ip_address
                )

                status_list.append({
                    "sim": raw,
                    "status": "success" if status == 1 else "error",
                    "message": msg
                })

            else:
                # Création SIM UAT
                cursor_uat.execute(
                    "INSERT INTO MEDIATION.SIM_TO_CREATE VALUES (:sim, NULL, NULL)",
                    sim=sim
                )
                cursor_uat.execute("CALL MEDIATION.CREATE_SIM_TEST()")
                conn_uat.commit()

                cursor_uat.execute("""
                    SELECT sm_status, dealer_id
                    FROM storage_medium
                    WHERE sm_serialnum=:sim
                """, sim=sim)
                row_created = cursor_uat.fetchone()

                if row_created:
                    sm_status, dealer_id = row_created
                    auc = creationauc([raw], env="UAT", is_file=is_file)
                    msg = "SIM created & AUC created in UAT" if auc.get("success") else auc.get("message")
                    status = 1 if auc.get("success") else 0
                else:
                    sm_status = dealer_id = None
                    msg = "SIM not found after creation in UAT"
                    status = 0

                log_sim_liberation(
                    action_type="UAT",
                    status=status,
                    created_by=username,
                    user_type=user_type,
                    num_sim=sim,
                    sim_status=sm_status,
                    dealer_id=dealer_id,
                    message=msg,
                    ip_address=ip_address
                )

                status_list.append({
                    "sim": raw,
                    "status": "success" if status == 1 else "error",
                    "message": msg
                })

        return {"success": True, "statusList": status_list}

    finally:
        close_connection(conn_uat, cursor_uat)
        close_connection(conn_prod, cursor_prod)





def liberate(user_inputs: List[str], env: str = "PROD", username: str = None, user_type: str = None, ip_address: str = None, is_file: bool = False) -> Dict[str, Any]:
    """
    Appelle la fonction liberate_prod ou liberate_uat en passant les informations utilisateur et ip_address
    """
    if env.upper() == "PROD":
        return liberate_prod(
            user_inputs=user_inputs,
            username=username,
            user_type=user_type,
            ip_address=ip_address,
            is_file=is_file
        )
    elif env.upper() == "UAT":
        return liberate_uat(
            user_inputs=user_inputs,
            username=username,
            user_type=user_type,
            ip_address=ip_address,
            is_file=is_file
        )
    else:
        return {"success": False, "statusList": [], "message": "Environment invalide"}



