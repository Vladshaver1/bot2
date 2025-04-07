import os
import json
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix
from datetime import datetime


class Base(DeclarativeBase):
    pass


db = SQLAlchemy(model_class=Base)
# create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "default-secret-key")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)  # needed for url_for to generate with https

# configure the database, relative to the app instance folder
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
# initialize the app with the extension, flask-sqlalchemy >= 3.0.x
db.init_app(app)


# Define models for web interface
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.BigInteger, unique=True, nullable=False)
    username = db.Column(db.String(64), nullable=True)
    full_name = db.Column(db.String(128), nullable=True)
    referral_id = db.Column(db.BigInteger, nullable=True)
    stars = db.Column(db.Integer, default=0)
    completed_tasks = db.Column(db.Integer, default=0)
    referrals_count = db.Column(db.Integer, default=0)
    last_activity = db.Column(db.DateTime, default=datetime.utcnow)
    is_banned = db.Column(db.Boolean, default=False)
    reg_date = db.Column(db.DateTime, default=datetime.utcnow)


class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(256), nullable=False)
    reward = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)


class UserTask(db.Model):
    user_id = db.Column(db.BigInteger, db.ForeignKey('user.user_id'), primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('task.id'), primary_key=True)
    completed_date = db.Column(db.DateTime, default=datetime.utcnow)


class Withdrawal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.BigInteger, db.ForeignKey('user.user_id'))
    amount = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(16), default='pending')
    request_date = db.Column(db.DateTime, default=datetime.utcnow)
    process_date = db.Column(db.DateTime, nullable=True)


class AdminSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    min_referrals = db.Column(db.Integer, default=35)
    min_tasks = db.Column(db.Integer, default=40)
    partner_bonus = db.Column(db.Integer, default=10)
    steal_percent = db.Column(db.Integer, default=1)
    steal_unlock_tasks = db.Column(db.Integer, default=25)


class GameStats(db.Model):
    user_id = db.Column(db.BigInteger, db.ForeignKey('user.user_id'), primary_key=True)
    game_name = db.Column(db.String(32), primary_key=True)
    games_played = db.Column(db.Integer, default=0)
    stars_won = db.Column(db.Integer, default=0)
    last_played = db.Column(db.DateTime, default=datetime.utcnow)


class SubgramExchange(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.BigInteger, db.ForeignKey('user.user_id'))
    stars_amount = db.Column(db.Integer, nullable=False)
    subgram_amount = db.Column(db.Float, nullable=False)
    exchange_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(16), default='completed')

class SubscriptionReward(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.BigInteger, db.ForeignKey('user.user_id'))
    channel_id = db.Column(db.String(64), nullable=False)
    channel_name = db.Column(db.String(128), nullable=False)
    stars_amount = db.Column(db.Integer, nullable=False)
    reward_date = db.Column(db.DateTime, default=datetime.utcnow)

class RequiredChannel(db.Model):
    channel_id = db.Column(db.String(64), primary_key=True)
    channel_name = db.Column(db.String(128), nullable=False)
    stars_reward = db.Column(db.Integer, default=10)
    added_date = db.Column(db.DateTime, default=datetime.utcnow)
    
class SubgramOffer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.BigInteger, db.ForeignKey('user.user_id'))
    offer_id = db.Column(db.String(128), nullable=True)  # ID оффера из Subgram, если есть
    channel_name = db.Column(db.String(128), nullable=True)  # Название канала, если есть
    offer_url = db.Column(db.String(256), nullable=False)  # URL для подписки
    reward_amount = db.Column(db.Integer, default=0)  # Награда в звездах
    status = db.Column(db.String(16), default='pending')  # pending, completed, rejected
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)


with app.app_context():
    db.create_all()
    
    # Add default admin settings if not already added
    settings = AdminSettings.query.first()
    if not settings:
        default_settings = AdminSettings()
        db.session.add(default_settings)
        db.session.commit()
    
    # Add default tasks if there are none
    tasks_count = Task.query.count()
    if tasks_count == 0:
        default_tasks = [
            Task(description='Подписаться на канал', reward=5),
            Task(description='Сделать репост', reward=10),
            Task(description='Оставить комментарий', reward=7)
        ]
        db.session.add_all(default_tasks)
        db.session.commit()


# Routes
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/dashboard')
def dashboard():
    users_count = User.query.count()
    tasks_count = Task.query.count()
    
    top_users = User.query.order_by(
        User.stars.desc(), User.referrals_count.desc()
    ).limit(10).all()
    
    pending_withdrawals = Withdrawal.query.filter_by(status='pending').count()
    subgram_exchanges_count = SubgramExchange.query.count()
    total_subgram_rubles = db.session.query(db.func.sum(SubgramExchange.subgram_amount)).scalar() or 0
    
    stats = {
        'users_count': users_count,
        'tasks_count': tasks_count,
        'pending_withdrawals': pending_withdrawals,
        'subgram_exchanges_count': subgram_exchanges_count,
        'total_subgram_rubles': round(total_subgram_rubles, 2)
    }
    
    return render_template('dashboard.html', stats=stats, top_users=top_users)


@app.route('/users')
def users_list():
    users = User.query.order_by(User.reg_date.desc()).all()
    return render_template('users.html', users=users)


@app.route('/tasks')
def tasks_list():
    tasks = Task.query.all()
    return render_template('tasks.html', tasks=tasks)


@app.route('/tasks/add', methods=['POST'])
def add_task():
    if request.method == 'POST':
        description = request.form.get('description')
        reward = int(request.form.get('reward', 0))
        
        if description and reward > 0:
            try:
                new_task = Task(description=description, reward=reward, is_active=True)
                db.session.add(new_task)
                db.session.commit()
                flash('Задание успешно добавлено', 'success')
            except Exception as e:
                flash(f'Ошибка при добавлении задания: {str(e)}', 'danger')
                db.session.rollback()
        else:
            flash('Необходимо заполнить все поля', 'warning')
    
    return redirect(url_for('tasks_list'))


@app.route('/tasks/edit/<int:task_id>', methods=['POST'])
def edit_task(task_id):
    task = Task.query.get_or_404(task_id)
    
    if request.method == 'POST':
        description = request.form.get('description')
        reward = int(request.form.get('reward', 0))
        
        if description and reward > 0:
            try:
                task.description = description
                task.reward = reward
                db.session.commit()
                flash('Задание успешно обновлено', 'success')
            except Exception as e:
                flash(f'Ошибка при обновлении задания: {str(e)}', 'danger')
                db.session.rollback()
        else:
            flash('Необходимо заполнить все поля', 'warning')
    
    return redirect(url_for('tasks_list'))


@app.route('/tasks/toggle/<int:task_id>')
def toggle_task(task_id):
    task = Task.query.get_or_404(task_id)
    
    try:
        task.is_active = not task.is_active
        db.session.commit()
        status = "активировано" if task.is_active else "деактивировано"
        flash(f'Задание успешно {status}', 'success')
    except Exception as e:
        flash(f'Ошибка при изменении статуса задания: {str(e)}', 'danger')
        db.session.rollback()
    
    return redirect(url_for('tasks_list'))


@app.route('/withdrawals')
def withdrawals_list():
    withdrawals = Withdrawal.query.order_by(Withdrawal.request_date.desc()).all()
    return render_template('withdrawals.html', withdrawals=withdrawals)


@app.route('/settings', methods=['GET', 'POST'])
def settings():
    admin_settings = AdminSettings.query.first()
    
    if request.method == 'POST':
        try:
            admin_settings.min_referrals = int(request.form.get('min_referrals'))
            admin_settings.min_tasks = int(request.form.get('min_tasks'))
            admin_settings.partner_bonus = int(request.form.get('partner_bonus'))
            admin_settings.steal_percent = int(request.form.get('steal_percent'))
            admin_settings.steal_unlock_tasks = int(request.form.get('steal_unlock_tasks'))
            
            db.session.commit()
            flash('Настройки успешно обновлены', 'success')
        except Exception as e:
            flash(f'Ошибка при обновлении настроек: {str(e)}', 'danger')
            db.session.rollback()
    
    return render_template('settings.html', settings=admin_settings)


@app.route('/subgram')
def subgram_exchanges():
    exchanges = SubgramExchange.query.order_by(SubgramExchange.exchange_date.desc()).all()
    
    # Get statistics
    total_stars = db.session.query(db.func.sum(SubgramExchange.stars_amount)).scalar() or 0
    total_rubles = db.session.query(db.func.sum(SubgramExchange.subgram_amount)).scalar() or 0
    exchanges_count = SubgramExchange.query.count()
    unique_users = db.session.query(db.func.count(db.distinct(SubgramExchange.user_id))).scalar() or 0
    
    stats = {
        'total_stars': total_stars,
        'total_rubles': round(total_rubles, 2),
        'exchanges_count': exchanges_count,
        'unique_users': unique_users
    }
    
    return render_template('subgram.html', exchanges=exchanges, stats=stats)

@app.route('/subscriptions')
def subscription_rewards():
    rewards = SubscriptionReward.query.order_by(SubscriptionReward.reward_date.desc()).all()
    
    # Get statistics
    total_stars = db.session.query(db.func.sum(SubscriptionReward.stars_amount)).scalar() or 0
    rewards_count = SubscriptionReward.query.count()
    unique_users = db.session.query(db.func.count(db.distinct(SubscriptionReward.user_id))).scalar() or 0
    
    stats = {
        'total_stars': total_stars,
        'rewards_count': rewards_count,
        'unique_users': unique_users
    }
    
    return render_template('subscriptions.html', rewards=rewards, stats=stats)

@app.route('/channels')
def channels_list():
    channels = RequiredChannel.query.order_by(RequiredChannel.added_date.desc()).all()
    return render_template('channels.html', channels=channels)

@app.route('/channels/add', methods=['POST'])
def add_channel():
    if request.method == 'POST':
        channel_id = request.form.get('channel_id')
        channel_name = request.form.get('channel_name')
        stars_reward = int(request.form.get('stars_reward', 10))
        
        if channel_id and channel_name:
            try:
                existing_channel = RequiredChannel.query.get(channel_id)
                if existing_channel:
                    flash('Канал с таким ID уже существует', 'warning')
                else:
                    new_channel = RequiredChannel(
                        channel_id=channel_id,
                        channel_name=channel_name,
                        stars_reward=stars_reward
                    )
                    db.session.add(new_channel)
                    db.session.commit()
                    flash('Канал успешно добавлен', 'success')
            except Exception as e:
                flash(f'Ошибка при добавлении канала: {str(e)}', 'danger')
                db.session.rollback()
        else:
            flash('Необходимо заполнить все поля', 'warning')
    
    return redirect(url_for('channels_list'))

@app.route('/channels/remove/<channel_id>', methods=['POST'])
def remove_channel(channel_id):
    channel = RequiredChannel.query.get_or_404(channel_id)
    
    try:
        db.session.delete(channel)
        db.session.commit()
        flash('Канал успешно удален', 'success')
    except Exception as e:
        flash(f'Ошибка при удалении канала: {str(e)}', 'danger')
        db.session.rollback()
    
    return redirect(url_for('channels_list'))





@app.route('/reset_stars', methods=['POST'])
def reset_stars():
    """Обнуление звезд у всех пользователей"""
    if request.method == 'POST':
        try:
            # Обнуляем звезды всех пользователей в PostgreSQL
            User.query.update({User.stars: 0})
            db.session.commit()
            
            # Импортируем и вызываем функцию синхронизации с SQLite
            from main import sync_postgres_to_sqlite
            
            # Синхронизируем данные с SQLite
            sync_result = sync_postgres_to_sqlite()
            
            if sync_result:
                flash('Звезды всех пользователей успешно обнулены!', 'success')
            else:
                flash('Звезды обнулены в веб-интерфейсе, но возникли проблемы с синхронизацией бота.', 'warning')
        except Exception as e:
            flash(f'Ошибка при обнулении звезд: {str(e)}', 'danger')
            db.session.rollback()
    
    return redirect(url_for('index'))


@app.route('/users/edit_stars/<int:user_id>', methods=['POST'])
def edit_user_stars(user_id):
    """Изменение баланса звезд пользователя"""
    user = User.query.filter_by(user_id=user_id).first_or_404()
    
    if request.method == 'POST':
        try:
            new_stars = int(request.form.get('stars', 0))
            if new_stars < 0:
                new_stars = 0
                
            user.stars = new_stars
            db.session.commit()
            
            # Импортируем и вызываем функцию синхронизации с SQLite
            from main import sync_postgres_to_sqlite
            
            # Синхронизируем данные с SQLite
            sync_result = sync_postgres_to_sqlite()
            
            if sync_result:
                flash(f'Баланс пользователя {user.full_name} успешно изменен!', 'success')
            else:
                flash(f'Баланс пользователя изменен в веб-интерфейсе, но возникли проблемы с синхронизацией бота.', 'warning')
        except Exception as e:
            flash(f'Ошибка при изменении баланса: {str(e)}', 'danger')
            db.session.rollback()
    
    return redirect(url_for('users_list'))


@app.route('/users/toggle_ban/<int:user_id>', methods=['POST'])
def toggle_user_ban(user_id):
    """Блокировка/разблокировка пользователя"""
    user = User.query.filter_by(user_id=user_id).first_or_404()
    
    try:
        user.is_banned = not user.is_banned
        db.session.commit()
        
        # Импортируем и вызываем функцию синхронизации с SQLite
        from main import sync_postgres_to_sqlite
        
        # Синхронизируем данные с SQLite
        sync_result = sync_postgres_to_sqlite()
        
        status = "заблокирован" if user.is_banned else "разблокирован"
        
        if sync_result:
            flash(f'Пользователь {user.full_name} успешно {status}!', 'success')
        else:
            flash(f'Пользователь {status} в веб-интерфейсе, но возникли проблемы с синхронизацией бота.', 'warning')
    except Exception as e:
        flash(f'Ошибка при изменении статуса пользователя: {str(e)}', 'danger')
        db.session.rollback()
    
    return redirect(url_for('users_list'))


@app.route('/subgram/offers')
def subgram_offers():
    """Страница с историей офферов от SubGram"""
    offers = SubgramOffer.query.order_by(SubgramOffer.created_at.desc()).all()
    
    # Статистика по офферам
    total_offers = SubgramOffer.query.count()
    completed_offers = SubgramOffer.query.filter_by(status='completed').count()
    pending_offers = SubgramOffer.query.filter_by(status='pending').count()
    rejected_offers = SubgramOffer.query.filter_by(status='rejected').count()
    total_rewards = db.session.query(db.func.sum(SubgramOffer.reward_amount)).scalar() or 0
    unique_users = db.session.query(db.func.count(db.distinct(SubgramOffer.user_id))).scalar() or 0
    
    stats = {
        'total_offers': total_offers,
        'completed_offers': completed_offers,
        'pending_offers': pending_offers,
        'rejected_offers': rejected_offers,
        'total_rewards': total_rewards,
        'unique_users': unique_users
    }
    
    return render_template('subgram_offers.html', offers=offers, stats=stats)

@app.route('/subgram/offers/add', methods=['POST'])
def add_subgram_offer():
    """Добавление оффера вручную (для тестирования)"""
    if request.method == 'POST':
        user_id = request.form.get('user_id')
        offer_url = request.form.get('offer_url')
        channel_name = request.form.get('channel_name', '')
        reward_amount = int(request.form.get('reward_amount', 0))
        
        if user_id and offer_url:
            try:
                new_offer = SubgramOffer(
                    user_id=user_id,
                    offer_url=offer_url,
                    channel_name=channel_name,
                    reward_amount=reward_amount,
                    status='pending'
                )
                db.session.add(new_offer)
                db.session.commit()
                flash('Оффер успешно добавлен', 'success')
            except Exception as e:
                flash(f'Ошибка при добавлении оффера: {str(e)}', 'danger')
                db.session.rollback()
        else:
            flash('Необходимо заполнить все обязательные поля', 'warning')
    
    return redirect(url_for('subgram_offers'))

@app.route('/subgram/offers/update/<int:offer_id>', methods=['POST'])
def update_subgram_offer(offer_id):
    """Обновление статуса оффера"""
    offer = SubgramOffer.query.get_or_404(offer_id)
    
    if request.method == 'POST':
        status = request.form.get('status')
        
        if status in ['pending', 'completed', 'rejected']:
            try:
                offer.status = status
                if status == 'completed' and not offer.completed_at:
                    offer.completed_at = datetime.utcnow()
                db.session.commit()
                flash('Статус оффера успешно обновлен', 'success')
            except Exception as e:
                flash(f'Ошибка при обновлении статуса оффера: {str(e)}', 'danger')
                db.session.rollback()
        else:
            flash('Некорректный статус', 'warning')
    
    return redirect(url_for('subgram_offers'))


@app.route('/api/subgram/log_offer', methods=['POST'])
def api_log_subgram_offer():
    """API endpoint для логирования офферов от SubGram"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "No data provided"}), 400
        
        user_id = data.get('user_id')
        offer_url = data.get('offer_url')
        
        if not user_id or not offer_url:
            return jsonify({"status": "error", "message": "Missing required fields"}), 400
        
        # Получаем дополнительные данные, если они есть
        channel_name = data.get('channel_name', '')
        offer_id = data.get('offer_id', '')
        reward_amount = data.get('reward_amount', 10)  # По умолчанию 10 звезд
        
        # Проверяем, не логировали ли мы уже этот оффер для этого пользователя
        existing_offer = SubgramOffer.query.filter_by(
            user_id=user_id, 
            offer_url=offer_url,
            status='pending'
        ).first()
        
        if existing_offer:
            return jsonify({
                "status": "success", 
                "message": "Offer already exists", 
                "offer_id": existing_offer.id
            }), 200
        
        # Создаем новую запись в базе данных
        new_offer = SubgramOffer(
            user_id=user_id,
            offer_id=offer_id,
            channel_name=channel_name,
            offer_url=offer_url,
            reward_amount=reward_amount,
            status='pending'
        )
        
        db.session.add(new_offer)
        db.session.commit()
        
        return jsonify({
            "status": "success", 
            "message": "Offer logged successfully", 
            "offer_id": new_offer.id
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/subgram/update_offer', methods=['POST'])
def api_update_subgram_offer():
    """API endpoint для обновления статуса оффера от SubGram"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "No data provided"}), 400
        
        user_id = data.get('user_id')
        offer_url = data.get('offer_url')
        status = data.get('status')
        
        if not user_id or not offer_url or not status:
            return jsonify({"status": "error", "message": "Missing required fields"}), 400
        
        if status not in ['pending', 'completed', 'rejected']:
            return jsonify({"status": "error", "message": "Invalid status value"}), 400
        
        # Находим оффер в базе данных
        offer = SubgramOffer.query.filter_by(
            user_id=user_id, 
            offer_url=offer_url
        ).order_by(SubgramOffer.created_at.desc()).first()
        
        if not offer:
            return jsonify({"status": "error", "message": "Offer not found"}), 404
        
        # Обновляем статус
        offer.status = status
        if status == 'completed' and not offer.completed_at:
            offer.completed_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            "status": "success", 
            "message": "Offer status updated successfully", 
            "offer_id": offer.id
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/stats')
def api_stats():
    users_count = User.query.count() 
    tasks_completed = db.session.query(db.func.count(UserTask.user_id)).scalar()
    stars_total = db.session.query(db.func.sum(User.stars)).scalar() or 0
    withdrawals_completed = Withdrawal.query.filter_by(status='approved').count()
    subgram_exchanges = SubgramExchange.query.count()
    subgram_offers_count = SubgramOffer.query.count()
    
    return jsonify({
        'users_count': users_count,
        'tasks_completed': tasks_completed,
        'stars_total': stars_total,
        'withdrawals_completed': withdrawals_completed,
        'subgram_exchanges': subgram_exchanges,
        'subgram_offers_count': subgram_offers_count
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)