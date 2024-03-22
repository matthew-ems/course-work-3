from flask import Flask, render_template, request, redirect, flash, session, url_for, abort, session
from sqlalchemy.orm import sessionmaker, relationship, scoped_session
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, DateTime, LargeBinary
import bcrypt
from sqlalchemy.sql import exists, or_
from datetime import datetime
from validate_email import validate_email
from flask_socketio import SocketIO

app = Flask(__name__)
app.config['SECRET_KEY'] = 'key'

engine = create_engine('sqlite:///data.db', echo=True)
socketio = SocketIO(app)

Base = declarative_base()

class User(Base):
    __tablename__ = 'user'
    user_id = Column(Integer, primary_key=True)
    username = Column(String, unique=True)
    email = Column(String, unique=True)
    password = Column(LargeBinary)
    company_staff = relationship("CompanyStaff", back_populates="user")
    user_role_id = Column(Integer, ForeignKey('user_role.user_role_id'))
    user_role = relationship("UserRole", back_populates="users")

class Company(Base):
    __tablename__ = 'company'
    company_id = Column(Integer, primary_key=True)
    name = Column(String)
    company_owner = Column(Integer, ForeignKey('user.user_id'))
    owner = relationship("User")
    staff = relationship("CompanyStaff", back_populates="company")
    agile_tables = relationship("AgileTable", back_populates="company")
    chat = relationship("CompanyChat", back_populates="company")

class CompanyStaff(Base):
    __tablename__ = 'staff'
    staff_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('user.user_id'))
    company_id = Column(Integer, ForeignKey('company.company_id'))
    user = relationship("User", back_populates="company_staff")
    company = relationship("Company", back_populates="staff")

class AgileTable(Base):
    __tablename__ = 'agile'
    agile_id = Column(Integer, primary_key=True)
    agile_name = Column(String)
    company_id = Column(Integer, ForeignKey('company.company_id'))
    company = relationship("Company", back_populates="agile_tables")
    cards = relationship("Card", back_populates="agile")

class Card(Base):
    __tablename__ = 'card'
    card_id = Column(Integer, primary_key=True)
    card_title = Column(String)
    card_description = Column(String)
    creator_id = Column(Integer, ForeignKey('user.user_id'))
    creator = relationship("User", backref="created_cards")
    status_card_id = Column(Integer, ForeignKey('status_card.status_card_id'), default=1)
    status_card = relationship("StatusCard", back_populates="cards")
    estimated_time = Column(DateTime)
    actual_time = Column(DateTime)
    agile_id = Column(Integer, ForeignKey('agile.agile_id'))
    agile = relationship("AgileTable", back_populates="cards")

class StatusCard(Base):
    __tablename__ = 'status_card'
    status_card_id = Column(Integer, primary_key=True)
    status_card_name = Column(String)
    cards = relationship("Card", back_populates="status_card")

class UserRole(Base):
    __tablename__ = 'user_role'
    user_role_id = Column(Integer, primary_key=True)
    user_role_name = Column(String)
    users = relationship("User", back_populates="user_role")


class CompanyChat(Base):
    __tablename__ = 'company_chat'
    chat_id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey('company.company_id'))
    company = relationship("Company", back_populates="chat")
    messages = relationship("Message", back_populates="company_chat")

class Message(Base):
    __tablename__ = 'message'
    message_id = Column(Integer, primary_key=True)
    content = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)
    author_id = Column(Integer, ForeignKey('user.user_id'))
    author = relationship("User")
    chat_id = Column(Integer, ForeignKey('company_chat.chat_id'))
    company_chat = relationship("CompanyChat", back_populates="messages")

Base.metadata.create_all(engine)
Session = scoped_session(sessionmaker(bind=engine))

@app.route('/')
def index():
    return render_template('registration.html')

@app.route('/registration', methods=['GET', 'POST'])
def registration():
    error = False
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        role_id = request.form['role']

        if not (username and email and password and role_id):
            error = True

        if not validate_email(email):
            error = True

        if error:
            return render_template('registration.html', error=error)

        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

        new_user = User(username=username, email=email, password=hashed_password, user_role_id=role_id)

        try:
            Session.add(new_user)
            Session.commit()
            return redirect('/login')
        except:
            error = True

    return render_template('registration.html', error=error)

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = False
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if not (username and password):
            flash('Both username and password are required!', 'error')
            error = True

        user = Session.query(User).filter_by(username=username).first()

        if user:
            if bcrypt.checkpw(password.encode('utf-8'), user.password):
                session['user_id'] = user.user_id
                session['username'] = user.username
                return redirect('/main')
            else:
                flash('Invalid username or password', 'error')
                error = True
        else:
            flash('User not found', 'error')
            error = True

        if error:
            return render_template('login.html', error=error)

    return render_template('login.html', error=error)

@app.route('/main')
def main():
    if 'user_id' in session:
        user_id = session['user_id']

        owned_companies = Session.query(Company).filter_by(company_owner=user_id).all()
        user_companies = Session.query(Company).join(CompanyStaff).filter(CompanyStaff.user_id == user_id).all()

        user = Session.query(User).filter_by(user_id=user_id).first()

        user_role_id = user.user_role_id
        user_role = Session.query(UserRole).filter_by(user_role_id=user_role_id).first().user_role_name

        return render_template('main.html', username=session['username'], user_id=user_id,
                               owned_companies=owned_companies, user_companies=user_companies, user_role=user_role)
    else:
        return redirect('/login')

@app.route('/add_company', methods=['GET', 'POST'])
def add_company():
    if request.method == 'GET':
        return render_template('add_company.html')
    elif request.method == 'POST':
        name = request.form['name']
        if not name:
            return render_template('add_company.html', error=True)

        user_id = session['user_id']
        new_company = Company(name=name, company_owner=user_id)
        Session.add(new_company)
        Session.commit()

        # Создаем чат для новой компании
        new_chat = CompanyChat(company=new_company)
        Session.add(new_chat)

        try:
            Session.commit()
            flash('Company and chat added successfully!', 'success')
            return redirect('/main')
        except IntegrityError:
            Session.rollback()
            flash('Failed to add chat for the company.', 'error')
            return redirect('/main')

'''
roles = [
    UserRole(user_role_name='Owner'),
    UserRole(user_role_name='Back-end'),
    UserRole(user_role_name='Front-end'),
    UserRole(user_role_name='3D'),
    UserRole(user_role_name='Designer')
]

# Добавляем роли в сессию и сохраняем их в базе данных
Session.add_all(roles)
Session.commit()

'''


@app.route('/company/<int:company_id>', methods=['GET', 'POST'])
def company(company_id):
    company = Session.query(Company).filter_by(company_id=company_id).first()
    user_id = session['user_id']
    is_owner = company.company_owner == user_id

    company_staff = Session.query(CompanyStaff).filter_by(company_id=company_id).all()

    for staff_member in company_staff:
        staff_member.user.companies = Session.query(Company).join(CompanyStaff).filter_by(user_id=staff_member.user_id).all()

    error = False  # Инициализируем error здесь

    if request.method == 'POST':
        if 'new_staff_username' in request.form:
            new_staff_username = request.form['new_staff_username']
            user_to_add = Session.query(User).filter_by(username=new_staff_username).first()
            if user_to_add:
                new_staff_member = CompanyStaff(user_id=user_to_add.user_id, company_id=company_id)
                Session.add(new_staff_member)
                Session.commit()
                return redirect(url_for('company', company_id=company_id))
        elif 'agile_name' in request.form:
            agile_name = request.form['agile_name']
            if agile_name != '':
                new_agile_table = AgileTable(agile_name=agile_name, company_id=company_id)
                Session.add(new_agile_table)
                Session.commit()
            else:
                error = True

    users_without_company_staff_or_owner = Session.query(User).filter(
        ~exists().where(CompanyStaff.user_id == User.user_id),
        ~exists().where(Company.company_owner == User.user_id)
    ).all()

    agile_tables = Session.query(AgileTable).filter(company_id == company_id)

    return render_template('company.html', company=company, company_staff=company_staff, is_owner=is_owner, add_user=users_without_company_staff_or_owner, agile_tables=agile_tables, error=error)


@app.route('/agile-table/<int:agile_id>')
def agile_table(agile_id):
    user_id = session['user_id']

    # Получаем все карточки одного пользователя
    user_cards = Session.query(Card).filter_by(creator_id=user_id).all()
    for card in user_cards:
        print(card.card_title)

    # Получаем таблицу Agile по указанному идентификатору
    agile_table = Session.query(AgileTable).get(agile_id)
    return render_template('agile_table.html', agile_table=agile_table)


@app.route('/agile-table/<int:agile_id>/create-card', methods=['GET', 'POST'])
def create_card(agile_id):
    if request.method == 'POST':
        card_title = request.form['card_title']
        card_description = request.form['card_description']
        estimated_time_str = request.form['estimated_time']

        # Check if any field is empty
        if not card_title or not card_description or not estimated_time_str:
            flash('All fields must be filled!', 'error')
            return render_template('create_card.html', agile_id=agile_id, error=True)

        try:
            estimated_time = datetime.strptime(estimated_time_str, '%H:%M')
        except ValueError:
            flash('Invalid estimated time format!', 'error')
            return render_template('create_card.html', agile_id=agile_id, error=True)

        user_id = session['user_id']
        new_card = Card(card_title=card_title, card_description=card_description,
                        creator_id=user_id, status_card_id=1, estimated_time=estimated_time, agile_id=agile_id)
        Session.add(new_card)
        Session.commit()
        flash('Card created successfully!', 'success')
        return redirect(url_for('agile_table', agile_id=agile_id))

    return render_template('create_card.html', agile_id=agile_id)

@app.route('/change-status/<int:card_id>', methods=['POST'])
def change_status(card_id):
    if request.method == 'POST':
        new_status_id = int(request.form['new_status_id'])
        card = Session.query(Card).get(card_id)
        if card:
            card.status_card_id = new_status_id
            Session.commit()
            flash('Card status successfully changed!', 'success')
        else:
            flash('Card not found!', 'error')
    return redirect(url_for('agile_table', agile_id=card.agile_id))

@app.route('/add-elapsed-time/<int:card_id>', methods=['POST'])
def add_elapsed_time(card_id):
    if request.method == 'POST':
        elapsed_time_str = request.form['elapsed_time']
        elapsed_time = datetime.strptime(elapsed_time_str, '%H:%M')
        card = Session.query(Card).get(card_id)
        if card:
            card.actual_time = elapsed_time
            Session.commit()
            flash('Elapsed time successfully added to the card!', 'success')
        else:
            flash('Card not found!', 'error')
    return redirect(url_for('agile_table', agile_id=card.agile_id))


@app.route('/remove_staff/<int:staff_id>', methods=['POST', 'DELETE'])
def remove_staff(staff_id):
    if request.method in ['POST', 'DELETE']:
        # Проверьте, является ли текущий пользователь владельцем компании
        if 'user_id' in session:
            user_id = session['user_id']
            staff = Session.query(CompanyStaff).get(staff_id)

            if staff:
                company = staff.company
                # Проверьте, имеет ли текущий пользователь право на удаление сотрудника
                if company.company_owner == user_id:
                    # Удалите сотрудника из компании
                    Session.delete(staff)
                    Session.commit()
                    flash('Staff member removed successfully!', 'success')
                else:
                    flash('You do not have permission to remove this staff member!', 'error')
            else:
                flash('Staff member not found!', 'error')
        else:
            flash('You need to login first!', 'error')

    return redirect(url_for('company', company_id=company.company_id))


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    flash('You have been logged out', 'info')
    return redirect('/login')


@app.route('/chat/<int:company_id>', methods=['GET', 'POST'])
def chat(company_id):
    print(company_id)
    if request.method == 'POST':
        # Получаем содержимое сообщения из формы
        content = request.form['messageInput']
        # Получаем пользователя из сессии
        user_id = session['user_id']
        user = Session.query(User).filter_by(user_id=user_id).first()
        # Получаем чат для текущей компании
        company_chat = Session.query(CompanyChat).filter_by(company_id=company_id).first()
        if company_chat:
            # Создаем новое сообщение
            new_message = Message(author=user, content=content, company_chat=company_chat)
            # Добавляем сообщение в базу данных
            Session.add(new_message)
            Session.commit()
            # Отправляем новое сообщение всем подключенным клиентам через WebSocket
            socketio.emit('new_message', {'author': user.username, 'content': content})
    # Получаем все сообщения из базы данных для текущей компании
    company_chat = Session.query(CompanyChat).filter_by(company_id=company_id).first()
    if company_chat:
        messages = company_chat.messages
    else:
        messages = []
    return render_template('chat.html', messages=messages, username=session['username'], company_id=company_id)


@socketio.on('new_message')
def handle_new_message(message):
    # Отправляем сообщение всем подключенным клиентам
    socketio.emit('new_message', message)


@app.route('/send_message', methods=['POST'])
def send_message():
    return redirect('/chat')


if __name__ == '__main__':
    app.run(debug=True, port=8000)
