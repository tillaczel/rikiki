from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone
import math

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///rikiki.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Database Models
class Player(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nickname = db.Column(db.String(50), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Player {self.nickname}>'

class Game(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    started_at = db.Column(db.DateTime, nullable=True)  # When first round was started
    ended_at = db.Column(db.DateTime, nullable=True)  # When game was completed or ended early
    is_active = db.Column(db.Boolean, default=True)
    current_round = db.Column(db.Integer, default=1)
    max_rounds = db.Column(db.Integer, nullable=False)
    round_direction = db.Column(db.String(10), default='up')  # 'up' or 'down'
    current_dealer_index = db.Column(db.Integer, default=0)  # Index of current dealer in player order
    ended_early = db.Column(db.Boolean, default=False)  # Whether game was ended early
    deck_type = db.Column(db.String(10), default='single')  # 'single' or 'double'
    force_conflict = db.Column(db.Boolean, default=True)  # Whether to force conflict (prevent equal sums)
    
    def __repr__(self):
        return f'<Game {self.id}>'

class GamePlayer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.Integer, db.ForeignKey('game.id'), nullable=False)
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=False)
    total_points = db.Column(db.Integer, default=0)
    
    game = db.relationship('Game', backref='game_players')
    player = db.relationship('Player', backref='game_players')

class Round(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.Integer, db.ForeignKey('game.id'), nullable=False)
    round_number = db.Column(db.Integer, nullable=False)
    cards_per_player = db.Column(db.Integer, nullable=False)
    is_completed = db.Column(db.Boolean, default=False)
    
    game = db.relationship('Game', backref='rounds')

class RoundResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    round_id = db.Column(db.Integer, db.ForeignKey('round.id'), nullable=False)
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=False)
    guess = db.Column(db.Integer, nullable=False)
    hits = db.Column(db.Integer, nullable=True)  # NULL until round is completed
    points = db.Column(db.Integer, nullable=True)  # NULL until round is completed
    
    round = db.relationship('Round', backref='results')
    player = db.relationship('Player', backref='round_results')

# Routes
@app.route('/')
def index():
    players = Player.query.all()
    active_games = Game.query.filter_by(is_active=True).order_by(Game.created_at.desc()).all()
    return render_template('index.html', players=players, active_games=active_games)

@app.route('/players', methods=['GET', 'POST'])
def players():
    if request.method == 'POST':
        nickname = request.form['nickname'].strip()
        
        if not nickname:
            flash('Nickname is required!', 'error')
            return redirect(url_for('players'))
        
        # Check if nickname already exists
        existing_player = Player.query.filter_by(nickname=nickname).first()
        if existing_player:
            flash(f'Player with nickname "{nickname}" already exists!', 'error')
            return redirect(url_for('players'))
        
        new_player = Player(nickname=nickname)
        db.session.add(new_player)
        db.session.commit()
        flash(f'Player "{nickname}" added successfully!', 'success')
        return redirect(url_for('players'))
    
    players = Player.query.all()
    return render_template('players.html', players=players)

@app.route('/edit_player/<int:player_id>', methods=['GET', 'POST'])
def edit_player(player_id):
    player = Player.query.get_or_404(player_id)
    
    if request.method == 'POST':
        new_nickname = request.form['nickname'].strip()
        
        if not new_nickname:
            flash('Nickname is required!', 'error')
            return redirect(url_for('edit_player', player_id=player_id))
        
        # Check if nickname already exists (excluding current player)
        existing_player = Player.query.filter_by(nickname=new_nickname).first()
        if existing_player and existing_player.id != player_id:
            flash(f'Player with nickname "{new_nickname}" already exists!', 'error')
            return redirect(url_for('edit_player', player_id=player_id))
        
        old_nickname = player.nickname
        player.nickname = new_nickname
        db.session.commit()
        flash(f'Player "{old_nickname}" updated to "{new_nickname}" successfully!', 'success')
        return redirect(url_for('players'))
    
    return render_template('edit_player.html', player=player)

@app.route('/delete_player/<int:player_id>', methods=['POST'])
def delete_player(player_id):
    player = Player.query.get_or_404(player_id)
    nickname = player.nickname
    
    # Check if player is in any active game
    active_games = Game.query.filter_by(is_active=True).all()
    for game in active_games:
        game_player = GamePlayer.query.filter_by(game_id=game.id, player_id=player_id).first()
        if game_player:
            flash(f'Cannot delete player "{nickname}" - they are in an active game!', 'error')
            return redirect(url_for('players'))
    
    db.session.delete(player)
    db.session.commit()
    flash(f'Player "{nickname}" deleted successfully!', 'success')
    return redirect(url_for('players'))

@app.route('/new_game', methods=['GET', 'POST'])
def new_game():
    if request.method == 'POST':
        player_order = request.form.get('player_order', '')
        
        if not player_order:
            flash('No players selected!', 'error')
            return redirect(url_for('new_game'))
        
        player_ids = player_order.split(',')
        
        if len(player_ids) < 2:
            flash('At least 2 players are required!', 'error')
            return redirect(url_for('new_game'))
        
        # Get deck type and force conflict setting
        deck_type = request.form.get('deck_type', 'single')
        force_conflict = request.form.get('force_conflict', 'yes') == 'yes'
        
        # Calculate max rounds based on deck type
        n_players = len(player_ids)
        if deck_type == 'double':
            max_cards_per_player = math.floor(103 / n_players)
        else:  # single deck
            max_cards_per_player = math.floor(51 / n_players)
        max_rounds = max_cards_per_player * 2 - 1
        
        # Create new game with random dealer
        import random
        initial_dealer_index = random.randint(0, len(player_ids) - 1)
        new_game = Game(max_rounds=max_rounds, current_dealer_index=initial_dealer_index, deck_type=deck_type, force_conflict=force_conflict)
        db.session.add(new_game)
        db.session.commit()
        
        # Add players to game in the specified order
        for player_id in player_ids:
            game_player = GamePlayer(game_id=new_game.id, player_id=int(player_id))
            db.session.add(game_player)
        
        # Create first round
        first_round = Round(
            game_id=new_game.id,
            round_number=1,
            cards_per_player=1
        )
        db.session.add(first_round)
        db.session.commit()
        
        flash('New game started!', 'success')
        return redirect(url_for('game', game_id=new_game.id))
    
    players = Player.query.all()
    return render_template('new_game.html', players=players)

@app.route('/game/<int:game_id>')
def game(game_id):
    game = Game.query.get_or_404(game_id)
    current_round = Round.query.filter_by(game_id=game_id, round_number=game.current_round).first()
    
    if not current_round:
        flash('No current round found!', 'error')
        return redirect(url_for('index'))
    
    # Get round results for current round
    round_results = RoundResult.query.filter_by(round_id=current_round.id).all()
    
    # Get all players in this game and order them by dealer
    game_players = GamePlayer.query.filter_by(game_id=game_id).all()
    
    # Order players: start from player after dealer, end with dealer
    n_players = len(game_players)
    dealer_index = game.current_dealer_index
    ordered_players = []
    
    # Add players starting from the one after dealer
    for i in range(n_players):
        player_index = (dealer_index + 1 + i) % n_players
        ordered_players.append(game_players[player_index])
    
    # Prepare chart data
    chart_data = {
        'labels': [],
        'datasets': []
    }
    
    # Get completed rounds for labels
    completed_rounds = [r for r in game.rounds if r.is_completed]
    
    # Always start with Round 0 (starting point)
    chart_data['labels'] = ['Round 0']
    
    # Add completed rounds
    for round_obj in completed_rounds:
        chart_data['labels'].append(f'Round {round_obj.round_number}')
    
    # Prepare datasets for each player
    for i, game_player in enumerate(game_players):
        player_data = {
            'label': game_player.player.nickname,
            'data': [],
            'borderColor': f'hsl({i * 360 // len(game_players)}, 70%, 50%)',
            'backgroundColor': f'hsla({i * 360 // len(game_players)}, 70%, 50%, 0.1)',
            'tension': 0.1
        }
        
        # Always start with 0 points
        player_data['data'] = [0]
        
        # Add cumulative points for completed rounds
        cumulative_points = 0
        for round_obj in completed_rounds:
            round_result = RoundResult.query.filter_by(
                round_id=round_obj.id, 
                player_id=game_player.player.id
            ).first()
            if round_result:
                cumulative_points += round_result.points
            player_data['data'].append(cumulative_points)
        
        chart_data['datasets'].append(player_data)
    
    force_conflict_value = getattr(game, 'force_conflict', True)
    
    # Calculate min/max points for color coding
    points = [gp.total_points for gp in game_players]
    min_points = min(points) if points else 0
    max_points = max(points) if points else 0
    point_range = max_points - min_points if max_points > min_points else 1
    
    return render_template('game.html', 
                         game=game, 
                         current_round=current_round,
                         round_results=round_results,
                         game_players=ordered_players,
                         chart_data=chart_data,
                         force_conflict=force_conflict_value,
                         min_points=min_points,
                         point_range=point_range)

@app.route('/submit_guesses', methods=['POST'])
def submit_guesses():
    game_id = request.form['game_id']
    round_id = request.form['round_id']
    
    game = Game.query.get_or_404(game_id)
    current_round = Round.query.get_or_404(round_id)
    
    # Clear existing guesses for this round
    RoundResult.query.filter_by(round_id=round_id).delete()
    
    # Collect guesses and validate
    total_guess = 0
    guesses = {}
    
    for key, value in request.form.items():
        if key.startswith('guess_'):
            player_id = int(key.split('_')[1])
            guess = int(value)
            guesses[player_id] = guess
            total_guess += guess
    
    # Check if total guesses equals number of cards (only if force_conflict is enabled)
    force_conflict = getattr(game, 'force_conflict', True)
    if force_conflict and total_guess == current_round.cards_per_player:
        flash(f'Total guesses ({total_guess}) cannot equal the number of cards ({current_round.cards_per_player}) in this round! Please adjust your guesses.', 'error')
        return redirect(url_for('game', game_id=game_id))
    
    # Add new guesses
    for player_id, guess in guesses.items():
        round_result = RoundResult(
            round_id=round_id,
            player_id=player_id,
            guess=guess
        )
        db.session.add(round_result)
    
    # Set started_at timestamp if this is the first round and game hasn't started yet
    if current_round.round_number == 1 and not game.started_at:
        game.started_at = datetime.now(timezone.utc)
    
    db.session.commit()
    flash('Guesses submitted successfully!', 'success')
    return redirect(url_for('game', game_id=game_id))

@app.route('/force_end_game/<int:game_id>', methods=['POST'])
def force_end_game(game_id):
    game = Game.query.get_or_404(game_id)
    game.is_active = False
    game.ended_early = True
    game.ended_at = datetime.now(timezone.utc)
    db.session.commit()
    flash('Game ended early!', 'warning')
    return redirect(url_for('game_summary', game_id=game_id))

@app.route('/submit_results', methods=['POST'])
def submit_results():
    game_id = request.form['game_id']
    round_id = request.form['round_id']
    
    game = Game.query.get_or_404(game_id)
    current_round = Round.query.get_or_404(round_id)
    
    # Update results and calculate points
    for key, value in request.form.items():
        if key.startswith('hits_'):
            player_id = int(key.split('_')[1])
            hits = int(value)
            
            round_result = RoundResult.query.filter_by(
                round_id=round_id, 
                player_id=player_id
            ).first()
            
            if round_result:
                round_result.hits = hits
                
                # Calculate points
                if round_result.guess == hits:
                    # Correct guess: 10 + 2*n_hits
                    round_result.points = 10 + 2 * hits
                else:
                    # Incorrect guess: -2*abs(guess-hits) (negative points)
                    round_result.points = -2 * abs(round_result.guess - hits)
    
    # Mark round as completed
    current_round.is_completed = True
    
    # Update total points for each player
    for round_result in RoundResult.query.filter_by(round_id=round_id).all():
        game_player = GamePlayer.query.filter_by(
            game_id=game_id, 
            player_id=round_result.player_id
        ).first()
        if game_player:
            game_player.total_points += round_result.points
    
    # Move to next round or end game
    if game.current_round < game.max_rounds:
        game.current_round += 1
        
        # Rotate dealer to next player
        n_players = len(GamePlayer.query.filter_by(game_id=game_id).all())
        game.current_dealer_index = (game.current_dealer_index + 1) % n_players
        
        # Calculate cards for next round
        if game.current_round <= game.max_rounds // 2 + 1:
            # Going up: 1, 2, 3, ..., max_cards_per_player
            cards_per_player = game.current_round
        else:
            # Going down: max_cards_per_player-1, max_cards_per_player-2, ..., 1
            max_cards = game.max_rounds // 2 + 1
            cards_per_player = max_cards - (game.current_round - max_cards)
        
        # Create next round
        next_round = Round(
            game_id=game_id,
            round_number=game.current_round,
            cards_per_player=cards_per_player
        )
        db.session.add(next_round)
    else:
        # Game finished
        game.is_active = False
        game.ended_at = datetime.now(timezone.utc)
        flash('Game completed!', 'success')
        return redirect(url_for('game_summary', game_id=game_id))
    
    db.session.commit()
    return redirect(url_for('game', game_id=game_id))

@app.route('/history')
def history():
    completed_games = Game.query.filter_by(is_active=False).order_by(Game.created_at.desc()).all()
    return render_template('history.html', games=completed_games)

@app.route('/game_summary/<int:game_id>')
def game_summary(game_id):
    game = Game.query.get_or_404(game_id)
    
    # Fix: Ensure completed games have ended_at timestamp
    if not game.is_active and not game.ended_at:
        game.ended_at = datetime.now(timezone.utc)
        db.session.commit()
    
    game_players = GamePlayer.query.filter_by(game_id=game_id).order_by(GamePlayer.total_points.desc()).all()
    rounds = Round.query.filter_by(game_id=game_id).order_by(Round.round_number).all()
    
    # Prepare chart data
    chart_data = {
        'labels': [],
        'datasets': []
    }
    
    # Get completed rounds for labels
    completed_rounds = [r for r in rounds if r.is_completed]
    
    # Always start with Round 0 (starting point)
    chart_data['labels'] = ['Round 0']
    
    # Add completed rounds
    for round_obj in completed_rounds:
        chart_data['labels'].append(f'Round {round_obj.round_number}')
    
    # Prepare datasets for each player (ordered by final points)
    for i, game_player in enumerate(game_players):
        player_data = {
            'label': game_player.player.nickname,
            'data': [],
            'borderColor': f'hsl({i * 360 // len(game_players)}, 70%, 50%)',
            'backgroundColor': f'hsla({i * 360 // len(game_players)}, 70%, 50%, 0.1)',
            'tension': 0.1
        }
        
        # Always start with 0 points
        player_data['data'] = [0]
        
        # Add cumulative points for completed rounds
        cumulative_points = 0
        for round_obj in completed_rounds:
            round_result = RoundResult.query.filter_by(
                round_id=round_obj.id, 
                player_id=game_player.player.id
            ).first()
            if round_result:
                cumulative_points += round_result.points
            player_data['data'].append(cumulative_points)
        
        chart_data['datasets'].append(player_data)
    
    # Calculate statistics
    total_rounds = len(completed_rounds)
    total_players = len(game_players)
    winner = game_players[0] if game_players else None
    max_points = winner.total_points if winner else 0
    min_points = game_players[-1].total_points if game_players else 0
    point_spread = max_points - min_points
    
    # Calculate average points per round for each player
    player_stats = []
    for game_player in game_players:
        total_rounds_played = len([r for r in completed_rounds if 
            RoundResult.query.filter_by(round_id=r.id, player_id=game_player.player.id).first()])
        avg_points_per_round = game_player.total_points / total_rounds_played if total_rounds_played > 0 else 0
        
        # Count correct guesses
        correct_guesses = 0
        total_guesses = 0
        for round_obj in completed_rounds:
            round_result = RoundResult.query.filter_by(
                round_id=round_obj.id, 
                player_id=game_player.player.id
            ).first()
            if round_result:
                total_guesses += 1
                if round_result.guess == round_result.hits:
                    correct_guesses += 1
        
        accuracy = (correct_guesses / total_guesses * 100) if total_guesses > 0 else 0
        
        player_stats.append({
            'player': game_player.player,
            'total_points': game_player.total_points,
            'avg_points_per_round': avg_points_per_round,
            'correct_guesses': correct_guesses,
            'total_guesses': total_guesses,
            'accuracy': accuracy
        })
    
    force_conflict_value = getattr(game, 'force_conflict', True)
    return render_template('game_summary.html', 
                         game=game, 
                         game_players=game_players,
                         rounds=rounds,
                         player_stats=player_stats,
                         chart_data=chart_data,
                         total_rounds=total_rounds,
                         total_players=total_players,
                         winner=winner,
                         max_points=max_points,
                         min_points=min_points,
                         point_spread=point_spread,
                         force_conflict=force_conflict_value)

@app.route('/edit_game/<int:game_id>', methods=['GET', 'POST'])
def edit_game(game_id):
    game = Game.query.get_or_404(game_id)
    rounds = Round.query.filter_by(game_id=game_id).order_by(Round.round_number).all()
    game_players = GamePlayer.query.filter_by(game_id=game_id).all()
    
    if request.method == 'POST':
        # Handle form submission
        for round_obj in rounds:
            for game_player in game_players:
                guess_key = f'guess_{round_obj.id}_{game_player.player.id}'
                hits_key = f'hits_{round_obj.id}_{game_player.player.id}'
                
                if guess_key in request.form and hits_key in request.form:
                    guess = int(request.form[guess_key])
                    hits = int(request.form[hits_key])
                    
                    # Find or create round result
                    round_result = RoundResult.query.filter_by(
                        round_id=round_obj.id,
                        player_id=game_player.player.id
                    ).first()
                    
                    if not round_result:
                        round_result = RoundResult(
                            round_id=round_obj.id,
                            player_id=game_player.player.id,
                            guess=guess,
                            hits=hits
                        )
                        db.session.add(round_result)
                    else:
                        round_result.guess = guess
                        round_result.hits = hits
                    
                    # Recalculate points
                    if round_result.guess == round_result.hits:
                        round_result.points = 10 + 2 * round_result.hits
                    else:
                        round_result.points = -2 * abs(round_result.guess - round_result.hits)
        
        # Recalculate total points for all players
        for game_player in game_players:
            total_points = 0
            for round_obj in rounds:
                round_result = RoundResult.query.filter_by(
                    round_id=round_obj.id,
                    player_id=game_player.player.id
                ).first()
                if round_result and round_result.points is not None:
                    total_points += round_result.points
            game_player.total_points = total_points
        
        # Mark all rounds as completed if they have results
        for round_obj in rounds:
            round_results = RoundResult.query.filter_by(round_id=round_obj.id).all()
            if round_results:
                round_obj.is_completed = True
        
        db.session.commit()
        flash('Game data updated successfully! Points and graph have been recalculated.', 'success')
        return redirect(url_for('game_summary', game_id=game_id))
    
    # Prepare data for template
    round_data = []
    for round_obj in rounds:
        round_info = {
            'round': round_obj,
            'players': []
        }
        
        for game_player in game_players:
            round_result = RoundResult.query.filter_by(
                round_id=round_obj.id,
                player_id=game_player.player.id
            ).first()
            
            round_info['players'].append({
                'game_player': game_player,
                'result': round_result
            })
        
        round_data.append(round_info)
    
    return render_template('edit_game.html', 
                         game=game, 
                         rounds=round_data,
                         game_players=game_players)



@app.route('/delete_game/<int:game_id>', methods=['POST'])
def delete_game(game_id):
    game = Game.query.get_or_404(game_id)
    
    # Delete all related data (cascade delete)
    # Delete round results first
    for round_obj in game.rounds:
        RoundResult.query.filter_by(round_id=round_obj.id).delete()
    
    # Delete rounds
    Round.query.filter_by(game_id=game_id).delete()
    
    # Delete game players
    GamePlayer.query.filter_by(game_id=game_id).delete()
    
    # Delete the game itself
    db.session.delete(game)
    db.session.commit()
    
    flash(f'Game #{game_id} has been permanently deleted.', 'success')
    return redirect(url_for('history'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0', port=5000) 