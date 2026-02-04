import os
from ldap3 import Server, Connection, ALL, SIMPLE
import re
from ldap3.utils.conv import escape_filter_chars


def bind_user(username, password):
    ldap_server = os.getenv("LDAP_SERVER")
    ldap_base_dn = os.getenv("LDAP_BASE_DN")

    if not ldap_server or not ldap_base_dn:
        raise ValueError("LDAP_SERVER or LDAP_BASE_DN is not set in environment variables")

    user_dn = f"{username}@{ldap_base_dn}"

    try:
        server = Server(ldap_server, get_info=ALL)
        conn = Connection(server, user=user_dn, password=password, authentication=SIMPLE)
        return conn.bind()
    except Exception as e:
        print(f"LDAP Error: {e}")
        return False

def get_user_type(username, password):
    user_groups = get_user_groups(username, password)
    if 'ADM Support 1515 Group' in user_groups:
        return 'support1515'
    if 'CRM IT Team' in user_groups:
        return 'crm_it_team'
    if 'Digital Factory Group' in user_groups:
        return 'digital_factory'
    if 'B2B Activations' in user_groups:
        return 'boa_activations'
    if 'RoamingTeam' in user_groups:
        return 'roaming_team'
    
    return None

def get_user_groups(username, password):
    ldap_server = os.getenv("LDAP_SERVER")
    ldap_base_dn = os.getenv("LDAP_BASE_DN")
    search_base = os.getenv("LDAP_SEARCH_BASE")

    if not ldap_server or not ldap_base_dn or not search_base:
        raise ValueError("One or more LDAP environment variables are not set")

    user_dn = f"{username}@{ldap_base_dn}"

    try:
        server = Server(ldap_server, get_info=ALL)
        conn = Connection(server, user=user_dn, password=password, auto_bind=True)

        safe_username = escape_filter_chars(username)

        conn.search(
            search_base=search_base,
            search_filter=f'(&(objectClass=user)(sAMAccountName={safe_username}))',
            attributes=['memberOf']
        )

        if not conn.entries:
            print("Utilisateur introuvable.")
            return []

        user_entry = conn.entries[0]
        direct_groups_dn = user_entry.memberOf.values if 'memberOf' in user_entry else []

        all_group_dns = set(direct_groups_dn)
        parent_group_dns = set()

        for group_dn in direct_groups_dn:
            safe_group_dn = escape_filter_chars(group_dn)
            conn.search(
                search_base=search_base,
                search_filter=f'(&(objectClass=group)(distinguishedName={safe_group_dn}))',
                attributes=['memberOf']
            )
            if conn.entries:
                group_entry = conn.entries[0]
                parents = group_entry.memberOf.values if 'memberOf' in group_entry else []
                parent_group_dns.update(parents)

        all_group_dns.update(parent_group_dns)

        groups_cns = [
            re.search(r'CN=([^,]+)', dn).group(1)
            for dn in all_group_dns if re.search(r'CN=([^,]+)', dn)
        ]

        return groups_cns

    except Exception as e:
        print(f"Erreur LDAP : {e}")
        return []

