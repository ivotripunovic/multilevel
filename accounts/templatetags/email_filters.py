from django import template

register = template.Library()


@register.filter
def mask_email(email):
    """
    Mask an email address with asterisks while keeping it distinguishable.
    Shows the first character of the local part, masks the rest, and shows the full domain.
    Examples:
    - john.doe@example.com -> j***@example.com
    - user@domain.com -> u***@domain.com
    - a@test.com -> a***@test.com
    """
    if not email or '@' not in email:
        return email
    
    try:
        local_part, domain = email.rsplit('@', 1)
        
        if len(local_part) == 0:
            return email
        
        # Show first character, mask the rest with asterisks
        masked_local = local_part[0] + '*' * max(3, len(local_part) - 1)
        
        return f"{masked_local}@{domain}"
    except (ValueError, IndexError):
        return email
