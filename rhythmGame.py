import pygame
import random
import csv
import time
from datetime import datetime
from typing import List, Dict, Optional
import os

# Define constants
WINDOW_WIDTH = 800
WINDOW_HEIGHT = 600
FPS = 60

# Color definitions
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
BLUE = (100, 149, 237)  # Soft blue
GREEN = (144, 238, 144)  # Soft green
RED = (205, 92, 92)      # Soft red
GRAY = (169, 169, 169)

# Game configurations
KEYS = ['D', 'F', 'J', 'K']
GAME_DURATION = 70 # Seconds
LEVELS = 5
NOTE_WIDTH = 80
NOTE_HEIGHT = 40
HIT_LINE_Y = WINDOW_HEIGHT - 100
BASIC_SPEED = 2
BLOCK_SPEED_ACCR = 0.0
LEVEL_SPEED_ACCR = 3.5
SPAWN_INTERVAL = 0.6 #1.0

class Note:
    """Note class representing falling blocks."""
    def __init__(self, lane: int, speed: float, y: float = 0):
        self.lane = lane
        self.x = (WINDOW_WIDTH // len(KEYS)) * lane + (WINDOW_WIDTH // len(KEYS) - NOTE_WIDTH) // 2
        self.y = y
        self.speed = speed
        self.state = 'active'  # active, hit, missed
        self.hit_time: Optional[float] = None
        self.start_hit_time: Optional[float] = None
        self.miss_time: Optional[float] = None

class DifficultyManager:
    """Difficulty manager that controls game difficulty."""
    def __init__(self):
        '''
        Supports manual adjustments
        levels = [
            {'speed': 2.0, 'acceleration': 0.1},  # Level 1: Basic speed
            {'speed': 2.5, 'acceleration': 0.15}, # Level 2: Slightly faster
            {'speed': 3.0, 'acceleration': 0.2},  # Level 3: Increased difficulty
            {'speed': 4.0, 'acceleration': 0.25}, # Level 4: Notes are noticeably faster
            {'speed': 5.0, 'acceleration': 0.3},  # Level 5: Challenge level
        ]
        '''
        self.levels = []        # levels is a list, and each element is a dictionary, which contains two key-value pairs: speed and acceleration. Set in set_levels.
        self.current_level = 1
        self.current_speed = 2.0
        self.current_acceleration = 0.0

    def set_levels(self, levels):
        """Set the speed and acceleration for each level."""
        self.levels = levels

    def set_level(self, level):
        """Set the difficulty for the current level."""
        self.current_level = level
        if level <= len(self.levels): 
            self.current_speed = self.levels[level - 1]['speed']
            self.current_acceleration = self.levels[level - 1]['acceleration']
        else:
            pass

    def get_speed(self, elapsed_time: float) -> float:
        """Get the current speed."""
        return self.current_speed

class DataCollector:
    """Data collector that records game data."""
    def __init__(self, player_name: str, mode: str):
        self.player_name = player_name
        self.mode = mode
        self.session_data = []
        self.start_time = time.time()
        self.level = 1

        # Ensure that the data folder exists
        if not os.path.exists('data'):
            os.makedirs('data')

        # Create a CSV file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.timestamp = timestamp
        self.filename = f"data/{player_name}_{mode}_{timestamp}.csv"

        # Write CSV header
        with open(self.filename, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'timestamp', 'level', 'lane', 'hit_status',
                'reaction_time', 'reaction_distance', 'speed'
            ])

    def record_hit(self, note: Note, level: int, hit_status: str):
        """Record a hit event."""
        timestamp = time.time() - self.start_time
        if note.hit_time and note.start_hit_time:
            reaction_time = note.hit_time - note.start_hit_time
        else:
            reaction_time = None
        if note.hit_time:
            reaction_distance = abs(note.y - HIT_LINE_Y)
        else:
            reaction_distance = None

        data = {
            'timestamp': int(timestamp * 1000),  # Integer milliseconds
            'level': level,
            'lane': note.lane,
            'hit_status': hit_status,
            'reaction_time': int(reaction_time * 1000) if reaction_time else None,
            'reaction_distance': int(reaction_distance) if reaction_distance else None,
            'speed': round(note.speed, 2)
        }

        self.session_data.append(data)

        # Write to CSV in real-time
        with open(self.filename, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                data['timestamp'],
                data['level'],
                data['lane'],
                data['hit_status'],
                data['reaction_time'],
                data['reaction_distance'],
                data['speed']
            ])

    def save_feedback(self, level: int, feedback: List[int], total_time: float, exited: bool):
        """Save feedback data."""
        self.level = level  # Set the current level
        feedback_filename = f"data/{self.player_name}_{self.mode}_feedback_{self.timestamp}.csv"
        # Ensure the header exists
        if not os.path.exists(feedback_filename):
            with open(feedback_filename, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'timestamp',
                    'level',
                    'satisfaction',
                    'enjoyment',
                    'frustration',
                    'game_duration',
                    'exited'
                ])
        # Append feedback data
        with open(feedback_filename, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                datetime.now(),
                level,
                *feedback,
                total_time,
                exited
            ])

    def analyze_data(self, total_time: float, exited: bool):
        """Analyze data and calculate dependent variables."""
        total_hits = sum(1 for d in self.session_data if d['hit_status'] == 'hit')
        total_notes = sum(1 for d in self.session_data if d['hit_status'] in ['hit', 'miss'])
        hit_rate = total_hits / total_notes if total_notes > 0 else 0

        # Hit rate for each lane
        lane_hits = {lane: 0 for lane in range(len(KEYS))}
        lane_totals = {lane: 0 for lane in range(len(KEYS))}
        for d in self.session_data:
            if d['hit_status'] in ['hit', 'miss']:
                lane_totals[d['lane']] += 1
                if d['hit_status'] == 'hit':
                    lane_hits[d['lane']] += 1

        lane_hit_rates = {lane: lane_hits[lane] / lane_totals[lane] if lane_totals[lane] > 0 else 0 for lane in range(len(KEYS))}

        # Reaction time
        reaction_times = [d['reaction_time'] for d in self.session_data if d['reaction_time'] is not None]
        avg_reaction_time = sum(reaction_times) / len(reaction_times) if reaction_times else 0

        # Reaction time for each lane
        lane_reaction_times = {lane: [] for lane in range(len(KEYS))}
        for d in self.session_data:
            if d['reaction_time'] is not None:
                lane_reaction_times[d['lane']].append(d['reaction_time'])
        avg_lane_reaction_times = {lane: (sum(times) / len(times)) if times else 0 for lane, times in lane_reaction_times.items()}

        # Incorrect hit rate
        total_incorrect_hits = sum(1 for d in self.session_data if d['hit_status'] == 'incorrect')
        total_effective_hits = total_hits + total_incorrect_hits
        incorrect_hit_rate = total_incorrect_hits / total_effective_hits if total_effective_hits > 0 else 0

        # Incorrect hit rate for each lane
        lane_incorrect_hits = {lane: 0 for lane in range(len(KEYS))}
        lane_effective_hits = {lane: 0 for lane in range(len(KEYS))}
        for d in self.session_data:
            if d['hit_status'] in ['hit', 'incorrect']:
                lane_effective_hits[d['lane']] += 1
                if d['hit_status'] == 'incorrect':
                    lane_incorrect_hits[d['lane']] += 1
        lane_incorrect_hit_rates = {lane: lane_incorrect_hits[lane] / lane_effective_hits[lane] if lane_effective_hits[lane] > 0 else 0 for lane in range(len(KEYS))}

        # Game duration and exit rate
        game_duration = total_time
        exit_rate = 1 if exited else 0

        # Save analysis data
        analysis_filename = f"data/{self.player_name}_{self.mode}_analysis_{self.timestamp}.csv"
        # Ensure header exists
        if not os.path.exists(analysis_filename):
            with open(analysis_filename, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'timestamp',
                    'level',
                    'hit_rate',
                    'lane_hit_rates',
                    'avg_reaction_time',
                    'avg_lane_reaction_times',
                    'incorrect_hit_rate',
                    'lane_incorrect_hit_rates',
                    'game_duration',
                    'exit_rate'
                ])
        # Append analysis data
        with open(analysis_filename, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                datetime.now(),
                self.level,
                hit_rate,
                lane_hit_rates,
                avg_reaction_time,
                avg_lane_reaction_times,
                incorrect_hit_rate,
                lane_incorrect_hit_rates,
                game_duration,
                exit_rate
            ])

        # Clear session data
        self.session_data = []

class NoteGenerator:
    """Note generator."""
    def __init__(self, difficulty_manager: DifficultyManager):
        self.difficulty_manager = difficulty_manager
        self.notes: List[Note] = []
        self.last_spawn_time = 0
        self.spawn_interval = SPAWN_INTERVAL # Initial spawn interval

    def update(self, current_time: float) -> None:
        """Update note generation."""
        speed = self.difficulty_manager.get_speed(current_time)
        # Adjust spawn interval based on speed
        #[Optional] self.spawn_interval = max(0.5, 2.0 - speed / 5.0)
        if current_time - self.last_spawn_time >= self.spawn_interval:
            lane = random.randint(0, len(KEYS) - 1)
            self.notes.append(Note(lane, speed))
            self.last_spawn_time = current_time

class Game:
    """Main game class."""
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Rhythm Game")

        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 36)

        self.mode = None
        self.player_name = None
        self.running = True
        self.paused = False
        self.in_menu = True
        self.game_over = False

    def init_game(self):
        """Initialize game state."""
        self.difficulty_manager = DifficultyManager()
        self.current_level = 1
        
        # Generate level speed list (based on mode)
        levels = []
        base_speed = BASIC_SPEED
        for i in range(LEVELS):
            level_speed = base_speed + i * LEVEL_SPEED_ACCR  # Increase speed for each level
            levels.append({'speed': level_speed, 'acceleration': BLOCK_SPEED_ACCR})
            
        if self.mode == 'normal':
            # In normal mode, speed is constant across levels
            pass
        
        elif self.mode == 'test':
            # In test mode, random speeds shuffled
            random.shuffle(levels)

        else:
            levels = []
        self.difficulty_manager.set_levels(levels)
        self.difficulty_manager.set_level(self.current_level)
        self.note_generator = NoteGenerator(self.difficulty_manager)
        self.data_collector = DataCollector(self.player_name, self.mode)
        self.start_time = time.time()
        self.combo = 0
        self.hits = 0
        self.incorrect_hits = 0
        self.total_notes = 0
        self.paused = False
        self.game_over = False
        self.hit_line_flash_timer = 0
        self.pause_start_time = None
        self.total_paused_time = 0
        self.current_time = 0  # Add current_time variable

    def handle_input(self):
        """Handle input."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    if not self.in_menu and not self.game_over:
                        self.paused = not self.paused
                        if self.paused:
                            self.pause_start_time = time.time()
                        else:
                            paused_duration = time.time() - self.pause_start_time
                            self.total_paused_time += paused_duration
                            self.pause_start_time = None
                elif event.key == pygame.K_s:
                    # Skip level
                    if self.confirm_action("Skip Level? (y/n)"):
                        self.skip_level()
                elif event.key == pygame.K_m:
                    # Return to main menu
                    if self.confirm_action("Return to Menu? (y/n)"):
                        self.return_to_menu()
                elif event.key == pygame.K_q:
                    # Quit game
                    if self.confirm_action("Quit Game? (y/n)"):
                        self.running = False

                # Handle input in the main menu
                if self.in_menu:
                    if event.key in [pygame.K_1, pygame.K_2]:
                        self.mode = "test" if event.key == pygame.K_1 else "normal"
                        self.get_player_name()
                        self.in_menu = False
                        self.init_game()
                else:
                    key = pygame.key.name(event.key).upper()
                    if key in KEYS:
                        self.handle_note_hit(key)

    def confirm_action(self, message):
        """Confirm an action."""
        confirmed = False
        waiting_for_input = True
        while waiting_for_input:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    exit()
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_y:
                        confirmed = True
                        waiting_for_input = False
                    elif event.key == pygame.K_n:
                        confirmed = False
                        waiting_for_input = False
            self.screen.fill(BLACK)
            prompt = self.font.render(message, True, WHITE)
            self.screen.blit(prompt, (WINDOW_WIDTH//2 - prompt.get_width()//2, WINDOW_HEIGHT//2))
            pygame.display.flip()
            self.clock.tick(FPS)
        return confirmed

    def handle_note_hit(self, key: str):
        """Handle note hit."""
        lane = KEYS.index(key)
        hit = False
        duplicate = False

        for note in self.note_generator.notes[:]:
            if note.lane == lane and note.state == 'active':
                if HIT_LINE_Y - NOTE_HEIGHT <= note.y <= HIT_LINE_Y:
                    # Can be hit
                    note.state = 'hit'
                    note.hit_time = time.time()
                    hit = True
                    self.combo += 1
                    self.hits += 1
                    self.total_notes += 1
                    self.data_collector.record_hit(note, self.current_level, 'hit')
                    self.note_generator.notes.remove(note)
                    break
                elif note.state == 'hit':
                    # Duplicate hit
                    duplicate = True
                    self.data_collector.record_hit(note, self.current_level, 'duplicated')
                    break

        if not hit and not duplicate:
            # Incorrect key press
            self.combo = 0
            dummy_note = Note(lane, self.difficulty_manager.current_speed, y=HIT_LINE_Y)
            dummy_note.hit_time = time.time()
            self.data_collector.record_hit(
                dummy_note,
                self.current_level,
                'incorrect'
            )
            self.incorrect_hits += 1
            self.hit_line_flash_timer = 0.2  # Red line flash duration

    def draw(self):
        """Draw the game screen."""
        self.screen.fill(BLACK)

        if self.in_menu:
            self.draw_menu()
        else:
            self.draw_game()

        pygame.display.flip()

    def draw_menu(self):
        """Draw the main menu."""
        title = self.font.render("Rhythm Game", True, WHITE)
        option1 = self.font.render("1. Test Mode", True, WHITE)
        option2 = self.font.render("2. Normal Mode", True, WHITE)

        self.screen.blit(title, (WINDOW_WIDTH//2 - title.get_width()//2, 200))
        self.screen.blit(option1, (WINDOW_WIDTH//2 - option1.get_width()//2, 300))
        self.screen.blit(option2, (WINDOW_WIDTH//2 - option2.get_width()//2, 350))

    def draw_game(self):
        """Draw the game interface."""
        # Draw lanes
        lane_width = WINDOW_WIDTH // len(KEYS)
        for i in range(len(KEYS)):
            pygame.draw.line(
                self.screen,
                GRAY,
                (lane_width * i, 0),
                (lane_width * i, WINDOW_HEIGHT),
                2
            )

        # Draw the judgment line
        hit_line_color = RED if self.hit_line_flash_timer > 0 else WHITE
        pygame.draw.line(
            self.screen,
            hit_line_color,
            (0, HIT_LINE_Y),
            (WINDOW_WIDTH, HIT_LINE_Y),
            2
        )

        # Draw notes
        for note in self.note_generator.notes:
            if note.state == 'active':
                color = BLUE
                pygame.draw.rect(
                    self.screen,
                    color,
                    (note.x, note.y, NOTE_WIDTH, NOTE_HEIGHT)
                )
            elif note.state == 'missed':
                color = RED
                pygame.draw.rect(
                    self.screen,
                    color,
                    (note.x, note.y, NOTE_WIDTH, NOTE_HEIGHT)
                )

        # Display game information
        if self.mode == "normal":
            self.draw_game_info()
        elif self.mode == "test":
            self.draw_test_info()

    def draw_game_info(self):
        """Draw game information."""
        time_left = max(0, GAME_DURATION - self.current_time)
        info_texts = [
            f"Time: {int(time_left)}",
            f"Level: {self.current_level}",
            f"Hits: {self.hits}",
            f"Combo: {self.combo}"
        ]

        for i, text in enumerate(info_texts):
            surface = self.font.render(text, True, WHITE)
            self.screen.blit(surface, (10, 10 + i * 30))

    def draw_test_info(self):
        """Draw test mode game information."""
        time_left = max(0, GAME_DURATION - self.current_time)
        info_text = f"Time: {int(time_left)}"
        surface = self.font.render(info_text, True, WHITE)
        self.screen.blit(surface, (10, 10))

    def get_player_name(self):
        """Get the player's name."""
        input_box = pygame.Rect(WINDOW_WIDTH//4, WINDOW_HEIGHT//2, WINDOW_WIDTH//2, 40)
        name = ""
        input_active = True

        while input_active:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    return

                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN:
                        self.player_name = name if name else "Player"
                        input_active = False
                    elif event.key == pygame.K_BACKSPACE:
                        name = name[:-1]
                    else:
                        name += event.unicode

            self.screen.fill(BLACK)
            txt_surface = self.font.render("Enter your name:", True, WHITE)
            input_txt = self.font.render(name, True, WHITE)

            self.screen.blit(txt_surface, (WINDOW_WIDTH//4, WINDOW_HEIGHT//2 - 50))
            pygame.draw.rect(self.screen, WHITE, input_box, 2)
            self.screen.blit(input_txt, (input_box.x + 5, input_box.y + 5))

            pygame.display.flip()
            self.clock.tick(FPS)

    def update(self):
        """Update game state."""
        if not self.paused and not self.in_menu and not self.game_over:
            self.current_time = time.time() - self.start_time - self.total_paused_time  # Update current_time

            # Update note generation
            self.note_generator.update(self.current_time)

            # Update note positions
            for note in self.note_generator.notes[:]:
                if note.state == 'active':
                    note.y += note.speed

                    # Set the time when the note becomes hittable
                    if note.start_hit_time is None and note.y >= HIT_LINE_Y - NOTE_HEIGHT:
                        note.start_hit_time = time.time()

                    # Check if the note has been missed
                    if note.y > HIT_LINE_Y and note.state == 'active':
                        note.state = 'missed'
                        note.miss_time = time.time()
                        self.combo = 0
                        self.data_collector.record_hit(note, self.current_level, 'miss')
                        self.total_notes += 1

                elif note.state == 'missed':
                    # Remove missed notes after a certain time
                    if time.time() - note.miss_time > 0.5:
                        self.note_generator.notes.remove(note)

            # Update the red line flash timer
            if self.hit_line_flash_timer > 0:
                delta_time = self.clock.get_time() / 1000.0  # Convert to seconds
                self.hit_line_flash_timer -= delta_time
                if self.hit_line_flash_timer < 0:
                    self.hit_line_flash_timer = 0

            # Check for level completion
            if self.current_time >= GAME_DURATION:
                self.show_feedback()
                self.current_level += 1
                if self.current_level > LEVELS:
                    self.game_over = True
                    self.in_menu = True
                else:
                    self.difficulty_manager.set_level(self.current_level)
                    self.note_generator = NoteGenerator(self.difficulty_manager)
                    self.start_time = time.time()
                    self.combo = 0
                    self.hits = 0
                    self.incorrect_hits = 0
                    self.total_paused_time = 0
                    self.current_time = 0  # Reset current_time

    def show_feedback(self, skipped=False):
        """Display feedback questionnaire."""
        questions = [
            "Sense of satisfaction (1-5):",
            "Sense of accomplishment (1-5):",
            "Sense of frustration (1-5):"
        ]
        answers = []
        current_question = 0

        while current_question < len(questions):
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    return

                if event.type == pygame.KEYDOWN:
                    if event.unicode in "12345":
                        answers.append(int(event.unicode))
                        current_question += 1

            self.screen.fill(BLACK)

            if current_question < len(questions):
                question_surface = self.font.render(
                    questions[current_question], True, WHITE
                )
                self.screen.blit(
                    question_surface,
                    (WINDOW_WIDTH//2 - question_surface.get_width()//2, WINDOW_HEIGHT//2)
                )

            pygame.display.flip()
            self.clock.tick(FPS)

        # Calculate game duration and exit rate
        total_time = self.current_time
        exited = skipped

        # Save feedback data
        self.data_collector.save_feedback(self.current_level, answers, total_time, exited)
        self.data_collector.analyze_data(total_time, exited)

    def skip_level(self):
        """Skip the current level."""
        self.show_feedback(skipped=True)
        self.current_level += 1
        if self.current_level > LEVELS:
            self.game_over = True
            self.in_menu = True
        else:
            self.difficulty_manager.set_level(self.current_level)
            self.note_generator = NoteGenerator(self.difficulty_manager)
            self.start_time = time.time()
            self.combo = 0
            self.hits = 0
            self.incorrect_hits = 0
            self.total_paused_time = 0
            self.current_time = 0

    def return_to_menu(self):
        """Return to the main menu."""
        self.show_feedback(skipped=True)
        self.in_menu = True
        self.game_over = True

    def run(self):
        """Run the game's main loop."""
        while self.running:
            self.handle_input()
            self.update()
            self.draw()
            self.clock.tick(FPS)

if __name__ == "__main__":
    game = Game()
    game.run()
