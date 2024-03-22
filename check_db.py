from app import *

users = Session.query(User).all()

for user in users:
    print(user.username, user.user_role_id)

compnies = Session.query(Company).all()
for company in compnies:
    print(company.company_id, company.name, company.company_owner)


stuff = Session.query(CompanyStaff).all()
for st in stuff:
    print(st.staff_id, st.user_id, st.company_id)

roles = Session.query(UserRole).all()
for role in roles:
    print(role.user_role_id, role.user_role_name)


status = Session.query(StatusCard).all()
for status in status:
    print(status.status_card_name)


cards = Session.query(Card).all()
for card in cards:
    print(card.card_id, card.card_title, card.card_description, card.status_card_id, card.actual_time, card.estimated_time, card.creator_id)

mes = Session.query(CompanyChat).all()
for me in mes:
    print(me.chat_id)