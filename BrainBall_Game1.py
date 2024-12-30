import pygame
import sys

pygame.init()

WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("EEG Brainball")

# initialize colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (200, 0, 0)
BLUE = (0, 0, 200)
GREEN = (0, 200, 0)
GREY = (200, 200, 200)
LIGHT_BLUE = (173, 216, 230)
LIGHT_RED = (255, 182, 193)

clock = pygame.time.Clock()
FPS = 60
ball_radius = 20
ball_speed = 5
push_speed = 3
push_distance = 50

# goal positions
LEFT_GOAL_X = ball_radius
RIGHT_GOAL_X = WIDTH - ball_radius

font = pygame.font.SysFont("Roboto Mono", 24)

class Ball:
    def __init__(self, x, y, color, controls, goal_direction):
        self.x = x
        self.y = y
        self.color = color
        self.controls = controls
        self.progress = 0
        self.rect = pygame.Rect(self.x - ball_radius, self.y - ball_radius, ball_radius*2, ball_radius*2)
        self.goal_direction = goal_direction
        self.key_presses = 0
        self.pushed = False
        self.push_direction = 0
        self.push_remaining = 0
        self.start_x = x
        self.goal_x = RIGHT_GOAL_X if goal_direction == 1 else LEFT_GOAL_X
    
    def handle_keys(self):
        if self.pushed:
            return

        keys = pygame.key.get_pressed()
        moved = False

        if keys[self.controls['left']] and self.x - ball_speed > ball_radius:
            self.x -= ball_speed
            moved = True
        if keys[self.controls['right']] and self.x + ball_speed < WIDTH - ball_radius:
            self.x += ball_speed
            moved = True

        if moved:
            self.update_rect()
            self.update_progress()

    def draw(self, surface):
        pygame.draw.circle(surface, self.color, (int(self.x), int(self.y)), ball_radius)

    def update_rect(self):
        self.rect.topleft = (self.x - ball_radius, self.y - ball_radius)

    def push_ball(self, direction):
        self.pushed = True
        self.push_direction = direction
        self.push_remaining = push_distance

    def move_pushed_ball(self):
        if self.pushed and self.push_remaining > 0:
            move_step = min(push_speed, self.push_remaining)
            new_x = self.x + (self.push_direction * move_step)
            
            # Check boundaries
            if new_x - ball_radius < LEFT_GOAL_X:
                self.x = LEFT_GOAL_X + ball_radius
                self.pushed = False
                return "left"
            elif new_x + ball_radius > RIGHT_GOAL_X:
                self.x = RIGHT_GOAL_X - ball_radius
                self.pushed = False
                return "right"
            else:
                self.x = new_x
            
            self.push_remaining -= move_step
            self.update_rect()
            self.update_progress()
            
            if self.push_remaining <= 0:
                self.pushed = False
        return None

    def update_progress(self):
        if self.goal_direction == 1:  # Moving right
            progress = ((self.x - self.start_x) / (self.goal_x - self.start_x)) * 100
        else:  # Moving left
            progress = ((self.start_x - self.x) / (self.start_x - self.goal_x)) * 100
        self.progress = max(0, min(100, progress))

def draw_progress(surface, player1, player2):
    # Progress bar player 1
    pygame.draw.rect(surface, GREEN, (50, 50, 200, 25))
    pygame.draw.rect(surface, RED, (50, 50, 2 * player1.progress, 25))
    progress_text1 = font.render(f"Player 1: {int(player1.progress)}%", True, BLACK)
    surface.blit(progress_text1, (50, 80))

    # Progress bar player 2
    pygame.draw.rect(surface, GREEN, (WIDTH - 250, 50, 200, 25))
    pygame.draw.rect(surface, BLUE, (WIDTH - 250, 50, 2 * player2.progress, 25))
    progress_text2 = font.render(f"Player 2: {int(player2.progress)}%", True, BLACK)
    surface.blit(progress_text2, (WIDTH - 250, 80))

def reset_game():
    global player1, player2, winner, loser
    player1.x = WIDTH // 4
    player1.y = HEIGHT // 2
    player1.progress = 0
    player1.key_presses = 0
    player1.pushed = False
    player1.push_direction = 0
    player1.push_remaining = 0
    player1.update_rect()
    
    player2.x = 3 * WIDTH // 4
    player2.y = HEIGHT // 2
    player2.progress = 0
    player2.key_presses = 0
    player2.pushed = False
    player2.push_direction = 0
    player2.push_remaining = 0
    player2.update_rect()
    
    winner = None
    loser = None

def check_game_end(player1, player2):
    if player1.x - ball_radius <= LEFT_GOAL_X:
        player2.progress = 100  # Player 2 thắng nên progress = 100%
        player1.progress = 0    # Player 1 thua nên progress = 0%
        return "Player 2", "Player 1"
    
    # Player 2 bị đẩy về vạch đích của mình (bên phải)
    if player2.x + ball_radius >= RIGHT_GOAL_X:
        player1.progress = 100  # Player 1 thắng nên progress = 100%
        player2.progress = 0    # Player 2 thua nên progress = 0%
        return "Player 1", "Player 2"
    
    # Kiểm tra thắng bằng progress
    if player1.progress >= 100:
        return "Player 1", "Player 2"
    if player2.progress >= 100:
        return "Player 2", "Player 1"
        
    return None, None

reset_button_rect = pygame.Rect(WIDTH // 2 - 75, HEIGHT // 2 + 50, 150, 50)
reset_button_color = LIGHT_BLUE
reset_button_hover_color = LIGHT_RED

running = True
winner = None
loser = None

# Initialize players
player1 = Ball(
    x=WIDTH // 4,
    y=HEIGHT // 2,
    color=RED,
    controls={
        'left': pygame.K_a,
        'right': pygame.K_d,
        'up': pygame.K_w,
        'down': pygame.K_s
    },
    goal_direction=1
)

player2 = Ball(
    x=3 * WIDTH // 4,
    y=HEIGHT // 2,
    color=BLUE,
    controls={
        'left': pygame.K_LEFT,
        'right': pygame.K_RIGHT,
        'up': pygame.K_UP,
        'down': pygame.K_DOWN
    },
    goal_direction=-1
)

while running:
    clock.tick(FPS)
    mouse_pos = pygame.mouse.get_pos()
    
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if winner and reset_button_rect.collidepoint(event.pos):
                reset_game()
        elif event.type == pygame.KEYDOWN:
            if not winner:
                if event.key in [player1.controls['left'], player1.controls['right'], player1.controls['up'], player1.controls['down']]:
                    player1.key_presses += 1
                if event.key in [player2.controls['left'], player2.controls['right'], player2.controls['up'], player2.controls['down']]:
                    player2.key_presses += 1

    if not winner:
        # Handle movement
        player1.handle_keys()
        player2.handle_keys()

        # Check collisions and push
        if player1.rect.colliderect(player2.rect) and not (player1.pushed or player2.pushed):
            if player1.key_presses > player2.key_presses:
                player2.push_ball(1 if player1.x < player2.x else -1)
            elif player2.key_presses > player1.key_presses:
                player1.push_ball(1 if player2.x < player1.x else -1)
            player1.key_presses = 0
            player2.key_presses = 0

        # Move pushed balls and check for game end
        if player1.pushed:
            result = player1.move_pushed_ball()
            if result:
                if result == "left": 
                    player2.progress = 100
                    player1.progress = 0
                    winner, loser = "Player 2", "Player 1"
                elif result == "right": 
                    player1.progress = 100
                    player2.progress = 0
                    winner, loser = "Player 1", "Player 2"

        if player2.pushed and not winner:
            result = player2.move_pushed_ball()
            if result:
                if result == "right": 
                    player1.progress = 100
                    player2.progress = 0
                    winner, loser = "Player 1", "Player 2"
                elif result == "left": 
                    player2.progress = 100
                    player1.progress = 0
                    winner, loser = "Player 2", "Player 1"

        # Check if game has ended
        if not winner:
            winner, loser = check_game_end(player1, player2)

    # drawing
    screen.fill(WHITE)
    
    # draw goal lines
    pygame.draw.line(screen, BLACK, (LEFT_GOAL_X, 0), (LEFT_GOAL_X, HEIGHT), 5)
    pygame.draw.line(screen, BLACK, (RIGHT_GOAL_X, 0), (RIGHT_GOAL_X, HEIGHT), 5)
    
    player1.draw(screen)
    player2.draw(screen)
    draw_progress(screen, player1, player2)

    if winner:
        win_text = font.render(f"{winner} wins!", True, GREEN)
        lose_text = font.render(f"{loser} loses!", True, RED)
        screen.blit(win_text, (WIDTH // 2 - win_text.get_width() // 2, HEIGHT // 2 - win_text.get_height() // 2 - 30))
        screen.blit(lose_text, (WIDTH // 2 - lose_text.get_width() // 2, HEIGHT // 2 - lose_text.get_height() // 2))

        # draw reset button
        current_color = reset_button_hover_color if reset_button_rect.collidepoint(mouse_pos) else reset_button_color
        pygame.draw.rect(screen, current_color, reset_button_rect)
        pygame.draw.rect(screen, BLACK, reset_button_rect, 2)
        reset_text = font.render("Reset Game", True, BLACK)
        screen.blit(reset_text, (
            reset_button_rect.x + (reset_button_rect.width - reset_text.get_width()) // 2,
            reset_button_rect.y + (reset_button_rect.height - reset_text.get_height()) // 2
        ))

    pygame.display.flip()