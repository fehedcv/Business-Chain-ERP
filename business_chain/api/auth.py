import frappe
import frappe.auth
from frappe.utils.password import get_decrypted_password, set_encrypted_password
from frappe.utils import generate_hash
from frappe.auth import update_password

@frappe.whitelist(allow_guest=True)
def agent_signup(full_name, email, password, phone):
    if frappe.db.exists("User", email):
        frappe.throw("An account with this email already exists.")

    parts = full_name.strip().split(" ", 1)
    user = frappe.get_doc({
        "doctype":           "User",
        "email":             email,
        "first_name":        parts[0],
        "last_name":         parts[1] if len(parts) > 1 else "",
        "full_name":         full_name,
        "phone":         phone,
        "send_welcome_email": 0,
        "enabled":           1,
    })
    user.append("roles", {"role": "Agent"})
    user.insert(ignore_permissions=True)
    update_password(email, password)
    frappe.db.commit()

    return {"status": "ok"}


@frappe.whitelist(allow_guest=True)
def mobile_login(usr, pwd):
    # 1. Authenticate credentials
    login_manager = frappe.auth.LoginManager()
    login_manager.authenticate(user=usr, pwd=pwd)
    login_manager.post_login()

    # 2. Check if keys already exist
    existing_key = frappe.db.get_value("User", usr, "api_key")

    if existing_key:
        # Already generated — decrypt and return
        try:
            api_secret = get_decrypted_password("User", usr, fieldname="api_secret")
            return {"api_key": existing_key, "api_secret": api_secret}
        except Exception:
            pass  # Secret missing/corrupt — regenerate below

    # 3. Generate new key/secret
    api_key    = generate_hash(length=15)
    api_secret = generate_hash(length=15)

    # api_key is a plain Data field
    frappe.db.set_value("User", usr, "api_key", api_key)

    # api_secret must be stored via set_encrypted_password
    # so get_decrypted_password can retrieve it correctly
    set_encrypted_password("User", usr, api_secret, fieldname="api_secret")

    frappe.db.commit()

    return {
        "api_key": api_key,
        "api_secret": api_secret,
    }

#api for password reset - takes email and correct password as input, and new password, and updates the password if the email and current password are correct
@frappe.whitelist(allow_guest=True)
def reset_password(email, current_password, new_password):
    # 1. Verify current credentials
    login_manager = frappe.auth.LoginManager()
    login_manager.authenticate(user=email, pwd=current_password)
    login_manager.post_login()

    # 2. Update to new password
    update_password(user=email, pwd=new_password)
    frappe.db.commit()

    return {"status": "ok"}