# 🎴 Rikiki Card Game App

A web-based application for managing Rikiki card games with player registration, game tracking, and historical statistics.

## Features

- **Player Management**: Register players with unique nicknames and full names
- **Game Tracking**: Start new games with selected players
- **Round Management**: Track guesses and results for each round
- **Scoring System**: Automatic point calculation based on game rules
- **History**: View completed games and detailed statistics
- **Responsive Design**: Works on desktop and mobile browsers

## Game Rules

- **Cards**: 52-card deck (1 trump card, 51 cards distributed)
- **Rounds**: Cards per player goes 1 → 2 → 3 → ... → max → ... → 3 → 2 → 1
- **Max Cards**: `floor(51 / number_of_players)`
- **Total Rounds**: `(max_cards × 2) - 1`
- **Scoring**:
  - Correct guess: `10 + 2 × hits` points
  - Wrong guess: `2 × |guess - hits|` points

## Installation

1. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the application**:
   ```bash
   python app.py
   ```

3. **Open your browser** and go to:
   ```
   http://localhost:5000
   ```

## Usage

### 1. Add Players
- Go to "Players" page
- Enter nickname (must be unique) and full name
- Click "Add Player"

### 2. Start a New Game
- Go to "New Game" page
- Select at least 2 players
- Click "Start New Game"

### 3. Play the Game
- For each round:
  1. **Submit Guesses**: Each player guesses how many tricks they'll win
  2. **Submit Results**: Enter actual tricks won by each player
  3. **Continue**: Move to next round automatically

### 4. View History
- Go to "History" page to see all completed games
- Click "View Details" for detailed round-by-round results

## Database

The app uses SQLite database (`rikiki.db`) which is automatically created when you first run the application. The database contains:

- **Players**: Registered players with nicknames and full names
- **Games**: Game sessions with round information
- **Rounds**: Individual rounds with cards per player
- **Results**: Player guesses, hits, and calculated points

## File Structure

```
rikiki/
├── app.py              # Main Flask application
├── requirements.txt    # Python dependencies
├── README.md          # This file
├── templates/         # HTML templates
│   ├── base.html
│   ├── index.html
│   ├── players.html
│   ├── new_game.html
│   ├── game.html
│   ├── history.html
│   └── game_history.html
└── rikiki.db         # SQLite database (created automatically)
```

## Technical Details

- **Backend**: Flask (Python)
- **Database**: SQLite with SQLAlchemy ORM
- **Frontend**: Bootstrap 5 for responsive design
- **Host**: Runs on `0.0.0.0:5000` (accessible from any device on your network)

## Troubleshooting

- **Port already in use**: Change the port in `app.py` line 280
- **Database issues**: Delete `rikiki.db` to reset the database
- **Browser issues**: Try refreshing the page or clearing browser cache

## License

This project is open source and available under the MIT License. 