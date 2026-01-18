from flask import Flask, request, jsonify
from flask_cors import CORS
from ldap_auth import bind_user, get_user_type
from creation_liberation_sim import creationauc, liberate, normalize_iccid
from flask_jwt_extended import create_access_token, JWTManager, jwt_required
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from datetime import datetime, timedelta, timezone
from logs import log_sim_liberation
import traceback

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# ⚡️ JWT
app.config["JWT_SECRET_KEY"] = "super-secret-key"
jwt = JWTManager(app)

@app.route('/auth/login', methods=['POST'])
def login():
    try:
        data = request.json
        username = data.get("username", "").lower().strip()
        password = data.get("password", "")
        ip_address = request.remote_addr

        if not username or not password:
            return jsonify({"message": "Username and password are required"}), 400

        # 🔐 LDAP authentication
        if not bind_user(username, password):
            log_sim_liberation(
                action_type="login",
                status=0,
                created_by=username,
                user_type=None,                      # ❌ pas encore connu
                message="Incorrect username or password",
                ip_address=ip_address
            )
            return jsonify({"message": "Incorrect username or password"}), 401

        # 🎯 Get user type from LDAP
        user_type = get_user_type(username, password)

        if not user_type:
            log_sim_liberation(
                action_type="login",
                status=0,
                created_by=username,
                user_type=None,
                message="Access denied",
                ip_address=ip_address
            )
            return jsonify({"message": "Access denied"}), 403

        # 🪪 Create JWT
        expires = timedelta(days=1)
        expires_date = datetime.now(timezone.utc) + expires

        access_token = create_access_token(
            identity=username,
            additional_claims={"userType": user_type},
            expires_delta=expires
        )

        # ✅ SUCCESS LOGIN LOG
        log_sim_liberation(
            action_type="login",
            status=1,
            created_by=username,
            user_type=user_type,                    # 👈 LOGGED HERE
            message="User logged in successfully",
            ip_address=ip_address
        )

        return jsonify({
            "message": "User Logged In",
            "accessToken": access_token,
            "tokenExpDate": expires_date.isoformat(),
            "user": {
                "username": username,
                "userType": user_type
            }
        }), 200

    except Exception as e:
        return jsonify({"message": str(e)}), 500


@app.route("/sim/creation-liberation", methods=["POST", "OPTIONS"])
@jwt_required()
def creation_liberation():

    if request.method == "OPTIONS":
        return jsonify({"status": "ok"}), 200

    try:
        # 🔐 Infos SÛRES depuis le JWT
        username = get_jwt_identity()
        claims = get_jwt()
        user_type = claims.get("userType")
        data = request.get_json()
        mode = data.get("mode")
        sims_input = data.get("data")
        env = data.get("environment", "UAT").upper()

        if not sims_input:
            return jsonify({"success": False, "message": "Aucun ICCID fourni"}), 400

        # --- Normalisation ---
        raw_sims = []
        if isinstance(sims_input, str):
            raw_sims = (
                [line.strip() for line in sims_input.splitlines() if line.strip()]
                if mode == "fichier"
                else [sims_input.strip()]
            )
        elif isinstance(sims_input, list):
            raw_sims = [s.strip() for s in sims_input if s.strip()]
        else:
            return jsonify({"success": False, "message": "Format des données invalide"}), 400

        mapping_raw_to_norm = {raw: normalize_iccid(raw) for raw in raw_sims}
        norm_sims = list(set(mapping_raw_to_norm.values()))

        # --- Appel liberate ---
        status_by_norm = {}
        if norm_sims:
            ip_address = request.remote_addr

            liberate_res = liberate(
                user_inputs=norm_sims,
                env=env,
                username=username,
                user_type=user_type,
                ip_address=ip_address,
                is_file=(mode == "fichier")
            )

            for s in liberate_res.get("statusList", []):
                status_by_norm[s["sim"]] = s

        # --- Résultat final ---
        result_list = []
        for raw, norm in mapping_raw_to_norm.items():
            base_status = status_by_norm.get(norm)
            if not norm:
                result_list.append({"sim": raw, "status": "error", "message": "ICCID invalide"})
            elif base_status:
                result_list.append({
                    "sim": raw,
                    "status": base_status["status"],
                    "message": base_status.get("message", "")
                })
            else:
                result_list.append({"sim": raw, "status": "error", "message": "ICCID introuvable"})

        success_count = sum(1 for r in result_list if r["status"] == "success")

        return jsonify({
            "success": True,
            "results": result_list,
            "message": f"{success_count} SIM traitées avec succès, {len(result_list) - success_count} anomalies."
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "message": f"Erreur interne: {str(e)}"}), 500


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5012, debug=True)
