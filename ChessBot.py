# **MIT License**
#
# Copyright (c) 2024 zzzzzarya (Noah Van Camp)
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.*
#
# **Disclaimer**
#
# This program is intended for educational purposes only and should not be used to engage in illegal activities, 
# such as cheating. The author of this program disclaims any liability for 
# any damages or losses resulting from the use of this program.
#

from __future__ import annotations

__author__ = "Noah Van Camp"

__email__ = "noahvc619@gmail.com"

__version__ = "1.0.3"

import io
import chess
import chess.pgn
import keyboard
import pyautogui
import threading
from stockfish import Stockfish
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.remote.webelement import WebElement

class ChessBot:
    """
    A bot that plays chess on Lichess using Stockfish for move calculation.
    Interacts with the web interface using Selenium and pyautogui to execute moves.
    """
    URL = "https://lichess.org"
    STOCKFISH_PATH = "your/stockfish/path"
    XPATHS = {
        'parent_moves': '//*[@id="main-wrap"]/main/div[1]/rm6/l4x',
        'board': '//*[@id="main-wrap"]/main/div[1]/div[1]',
        'ranks': '//*[@id="main-wrap"]/main/div[1]/div[1]/div/cg-container/coords[1]',
        'top_time': '//*[@id="main-wrap"]/main/div[1]/div[7]/div[2]',
        'bottom_time': '//*[@id="main-wrap"]/main/div[1]/div[8]/div[2]',
        'clock': '//*[@id="main-wrap"]/main/div[1]/div[7]'
    }
    # Tweak these settings as you see fit
    DRAG_DURATION_SHORT = 0
    DRAG_DURATION_LONG = 0.3

    def __init__(self) -> None:
        """
        Initializes the ChessBot by setting up the webdriver, Stockfish engine,
        and starting the browser worker thread.
        """
        self.driver = self.initialize_webdriver()
        self.stockfish = self.initialize_stockfish()
        self.wait = WebDriverWait(self.driver, 1)
        self.color = None
        self.flag = False
        self.track_clock = False
        self.bongcloud = False
        self.show_move = False
        
        # Start the browser in a separate thread
        self.worker_thread = threading.Thread(target=self.initialize_browser)
        self.worker_thread.daemon = True
        self.worker_thread.start()
        
        # Listen for ESC key to exit the program
        self.wait_for_esc()
        
    def wait_for_esc(self) -> None:
        """Waits for the ESC key to be pressed to exit the program."""
        keyboard.wait('esc')
        self.exit_program()
        
    def initialize_webdriver(self) -> webdriver.Chrome:
        """
        Initializes the Chrome WebDriver with certain options.
        Returns:
            WebDriver: The initialized Chrome WebDriver.
        """
        options = webdriver.ChromeOptions()
        options.add_argument("--disable-extensions")
        driver = webdriver.Chrome(options=options)
        return driver

    def initialize_stockfish(self) -> Stockfish:
        """
        Initializes the Stockfish engine with specified parameters.
        Returns:
            Stockfish: The initialized Stockfish engine.
        """
        stockfish = Stockfish(path=self.STOCKFISH_PATH, depth=15, parameters={
            "Debug Log File": "",
            "Contempt": 0,
            "Min Split Depth": 0,
            "Threads": 7,
            "Ponder": "false",
            "Hash": 8192,
            "MultiPV": 1,
            "Skill Level": 20,
            "Move Overhead": 10,
            "Minimum Thinking Time": 10,
            "Slow Mover": 10,
            "UCI_Chess960": "false",
            "UCI_LimitStrength": "false",
            "UCI_Elo": 1350
        })
        return stockfish
    
    def exit_program(self) -> None:
        """Exits the program by closing the WebDriver and quitting the script."""
        print("\nExiting the program.")
        self.driver.quit()
        quit()
        
    def initialize_browser(self) -> None:
        """Loads the Lichess website and starts the game loop."""
        self.driver.get(self.URL)
        try:
            self.gameloop()
        except Exception as e:
            print(f"An error has occured: {e}")

    def determine_color(self, ranks: WebElement) -> str:
        """
        Determines the color of the player based on the ranks' class attribute.
        Args:
            ranks (WebElement): The ranks element containing the class attribute.
        Returns:
            str: "black" if playing as black, "white" otherwise.
        """
        class_name = ranks.get_attribute("class")
        if class_name == "ranks black":
            print("Playing as black"); return "black"
        print("Playing as white"); return "white"
    
    def wait_for_ranks(self) -> WebElement:
        """
        Waits until the ranks element is present on the page.
        Returns:
            WebElement: The ranks element.
        """
        while True:
            try:
                return self.wait_for_element("ranks")
            except Exception:
                pass
                
    def initialize_game(self) -> None:
        """
        Initializes the game state by determining player color, checking if the game is timed,
        and setting up the initial board state. Executes the opening move if applicable.
        """
        self.moves_elements = []
        self.moves = []
        self.time = False
        ranks = self.wait_for_ranks()
        clock = self.wait_for_element('clock')
        self.time = len(clock.find_elements(By.XPATH, ".//*")) > 1; print(f"Game is {'timed' if self.time else 'not timed'}!")
        self.color = self.determine_color(ranks)
        self.get_board_coords()

        if not self.bongcloud:
            if self.color == "white":
                self.execute_move("e2e4")
            self.stockfish.set_position()
        else:
            self.execute_bongcloud_moves()
            self.get_moves()
            pgn_string = " ".join(self.moves)
            pgn = chess.pgn.read_game(io.StringIO(pgn_string))
            board = chess.Board()
            moves = []
            for move in pgn.mainline_moves():
                board.push(move)
                moves.append(str(move))
            self.stockfish.set_position(moves[:-1])

    def execute_bongcloud_moves(self) -> None:
        """
        Executes the Bongcloud opening (1. e3, 2. Ke2, 3. Ke1 for white; e6, Ke7, Ke8 for black)
        and waits for the opponent's move in between.
        """
        if self.color == "white":
            moves = ["e2e3", "e1e2", "e2e1"]
        else:
            moves = ["e7e6", "e8e7", "e7e8"]
        for move in moves:
            while not self.is_turn() and not self.flag:
                pass
            if self.flag:
                break
            self.execute_move(move)

    def get_moves(self) -> None:
        """Fetches the latest moves from the game and updates the move list."""
        try:
            parent_moves_element = self.wait_for_element("parent_moves")
            if self.time and self.track_clock:
                self.update_clock_times()
            new_moves = parent_moves_element.find_elements(By.XPATH, ".//*")
            filtered_new_moves = [move for move in new_moves if move not in self.moves_elements]
            self.moves_elements.extend(filtered_new_moves)
            self.moves.extend([move.text + "." if move.text.isdigit() else move.text for move in filtered_new_moves])
        except Exception:
            pass
        
    def update_clock_times(self) -> None:
        """Updates the clock times for both players if the game is timed."""
        try:
            top_time = self.wait_for_element('top_time').text
            bottom_time = self.wait_for_element('bottom_time').text
            if self.color == "white":
                btime = top_time.replace("\n", "")
                wtime = bottom_time.replace("\n", "")
            else:
                wtime = top_time.replace("\n", "")
                btime = bottom_time.replace("\n", "")
            self.wtime = (int(wtime[:wtime.index(":")])*60 + int(wtime[wtime.index(":")+1:]))*1000
            self.btime = (int(btime[:btime.index(":")])*60 + int(btime[btime.index(":")+1:]))*1000
        except TimeoutException:
            pass
        
    def handle_end_game(self) -> bool:
        """
        Checks for game-ending conditions such as victory or draw.
        Returns:
            bool: False if the game is over, True otherwise.
        """
        if "victorious" in self.moves[-1].lower():
            self.flag = True
            if "white is victorious" in self.moves[-1].lower() and self.color == "white":
                print("We win!")
            elif "white is victorious" in self.moves[-1].lower() and self.color == "black":
                print("We lost!")
            elif "black is victorious" in self.moves[-1].lower() and self.color == "black":
                print("We win!")
            else:
                print("We lost!")
            return False
        elif any(word in self.moves[-1].lower() for word in ["draw", "aborted"]):
            self.flag = True
            print("It's a draw!")
            return False
        else:
            return True
        
    def is_turn(self) -> bool:
        """
        Determines if it's the bot's turn to move.
        Returns:
            bool: True if it's the bot's turn, False otherwise.
        """
        self.get_moves()
        if not self.moves:
            if self.color == "black":
                return False
            return True
        if not self.handle_end_game():
            return False
        return self.determine_turn()

    def determine_turn(self) -> bool:
        """
        Determines if it's the bot's turn based on the current move list.
        Returns:
            bool: True if it's the bot's turn, False otherwise.
        """
        if self.color == "white":
            return (len(self.moves) % 3 == 0)
        else:
            return ((len(self.moves)-2) % 3 == 0)

    def get_next_move(self) -> None:
        """
        Determines the best move using Stockfish and executes it on the board.
        """
        pgn_string = " ".join(self.moves)
        pgn = chess.pgn.read_game(io.StringIO(pgn_string))
        board = chess.Board()
        moves = []
        for move in pgn.mainline_moves():
            board.push(move)
            if len(moves) >= 2:
                moves.pop(0)
            moves.append(str(move))
        try:
            self.stockfish.make_moves_from_current_position(moves)
        except ValueError:
            print("pyautogui needs a moment..")
        best_move = self.stockfish.get_best_move_time(10)
        if best_move:
            self.execute_move(str(best_move))
        else:
            self.flag = True

    def get_board_coords(self) -> None:
        """Calculates and stores the board coordinates for each square."""
        element = self.wait_for_element('board')
        element_x, element_y = element.location.values()
        driver_x, _ = self.driver.get_window_position().values()
        height, width = element.size.values()
        corrected_x, corrected_y = [a + b for a, b in zip((element_x, element_y), [self.driver.execute_script(f'return window.outer{word} - window.inner{word};') for word in ["Width", "Height"]])]
        abs_x, abs_y = corrected_x + driver_x, corrected_y
        files = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h']
        ranks = [1, 2, 3, 4, 5, 6, 7, 8]
        self.positions = self.calculate_positions(files, ranks, abs_x, abs_y, width, height)

    def calculate_positions(
        self, 
        files: list[str], 
        ranks: list[int], 
        abs_x: int, 
        abs_y: int, 
        width: int, 
        height: int
    ) -> dict[str, tuple[int, int]]:
        """
        Calculates the screen positions for each square on the chessboard.
        Args:
            files (list): List of file letters (a-h).
            ranks (list): List of rank numbers (1-8).
            abs_x (int): The absolute X position of the top-left corner of the board.
            abs_y (int): The absolute Y position of the top-left corner of the board.
            width (int): The width of the board.
            height (int): The height of the board.
        Returns:
            dict: A dictionary mapping square names (e.g., 'e2') to screen coordinates (x, y).
        """
        if self.color == "white":
            return {
                f'{file}{rank}': (
                    round((width / 8) * files.index(file) + (width / 8) / 2 + abs_x),
                    round((height / 8) * (8 - rank) + (height / 8) / 2 + abs_y)
                )
                for file in files for rank in ranks
            }
        else:
            return {
                f'{file}{rank}': (
                    round((width / 8) * list(reversed(files)).index(file) + (width / 8) / 2 + abs_x),
                    round((height / 8) * (rank - 1) + (height / 8) / 2 + abs_y)
                )
                for file in list(reversed(files)) for rank in ranks
            }

    def execute_move(self, move: str) -> None:
        """
        Executes the given move on the board using pyautogui.
        Args:
            move (str): The move in UCI format (e.g., 'e2e4').
        """
        from_x, from_y = self.positions[move[:2]]
        to_x, to_y = self.positions[move[2:4]]
        pyautogui.moveTo(x=from_x, y=from_y)
        if move[-1].isdigit():
            pyautogui.dragTo(x=to_x, y=to_y, duration=self.DRAG_DURATION_LONG if self.show_move else self.DRAG_DURATION_SHORT, button="secondary" if self.show_move else "primary")
        else:
            pyautogui.dragTo(x=to_x, y=to_y, duration=self.DRAG_DURATION_LONG if self.show_move else self.DRAG_DURATION_SHORT, button="secondary" if self.show_move else "primary")
            self.handle_promotion(move)

    def handle_promotion(self, move: str) -> None:
        """
        Handles pawn promotion by selecting the appropriate piece.
        Args:
            move (str): The move in UCI format including promotion (e.g., 'e7e8q').
        """
        if move[-1] in "qnrb":
            move_adjustments = {"q": 0,"n": -1,"r": -2,"b": -3}
            adjustment = move_adjustments.get(move[-1], 0)
            
            if self.color == "black":
                adjustment = -adjustment
                
            adjusted_rank = str(int(move[3]) + adjustment)
            promotion_position = f"{move[2]}{adjusted_rank}"
            pyautogui.click(y=self.positions[promotion_position][1])

    def wait_for_element(self, xpath_key: str) -> WebElement:
        """
        Waits until an element specified by its XPath key is present on the page.
        Args:
            xpath_key (str): The key for the desired element in the XPATHS dictionary.
        Returns:
            WebElement: The desired web element.
        """
        return self.wait.until(EC.presence_of_element_located((By.XPATH, self.XPATHS[xpath_key])))

    def gameloop(self) -> None:
        """Main game loop that initializes the game and handles moves until the game ends."""
        while True:
            self.initialize_game()
            while not self.flag:
                while not self.is_turn() and not self.flag:
                    pass
                if not self.flag:
                    self.get_next_move()
            self.handle_user_input()

    def handle_user_input(self) -> None:
        """Handles user input after a game ends to either start a new game or exit."""
        print("\nGame Over. Press 'ENTER' to continue, or 'ESC' to exit the program.")
        keyboard.wait('enter')
        self.flag = False

if __name__ == "__main__":
    ChessBot()
