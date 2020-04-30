import io_functions
import check_turn as check
import math_functions as mf
import generate_turns as gt
from field import Field


from collections import defaultdict
from itertools import product
from threading import Thread
from multiprocessing import Process
from multiprocessing import Manager
# from tqdm import tqdm
import os
import sys


class Turn:
    def __init__(self, start_pos, end_pos, color):
        self.start_pos = start_pos
        self.end_pos = end_pos
        self.color = color

    def print(self):
        print("start pos: ({0}, {1})".format(*self.start_pos))
        print("start pos: ({0}, {1})".format(*self.end_pos))


class ThreadRet(Thread):
    def __init__(self, group=None, target=None, name=None,
                 args=(), kwargs={}, Verbose=None):
        Thread.__init__(self, group, target, name, args, kwargs)
        self._return = None

    def run(self):
        if self._target is not None:
            print("start thread:", self.name)
            self._return = self._target(*self._args,
                                        **self._kwargs)

    def join(self):
        Thread.join(self)
        print("end thread:", self.name)
        return self._return


def get_num_threads():
    if len(sys.argv) >= 2:
        return int(sys.argv[1])

    return (int)(os.popen('grep -c cores /proc/cpuinfo').read())


class Logic:
    def __init__(self):
        print("Init game logic class")

    def start(self, plate, data):
        color = 1
        self.figures_cost = data.data["FIGURES_COST"]

        global DATA
        DATA = data
        while True:
            io_functions.print_field(plate.field, data)
            now_turn = io_functions.get_turn(self, color, plate)

            plate.do_turn(now_turn)

            color = 3 - color

            print(plate.calculate_plate_cost(color, self.figures_cost))
            self.depth = [0, 0, 0, 0, 0]

            tmp = self.root_ai_turn(plate, color, 5)
            now_turn = tmp[0]
            print("depht 5:", self.depth[0])
            print("depht 4:", self.depth[1])
            print("depht 3:", self.depth[2])
            print("depht 2:", self.depth[3])
            print("depht 1:", self.depth[4])
            now_turn.print()
            plate.do_turn(now_turn)

            color = 3 - color

    def check_turn(self, turn, plate):
        if (not plate.check_pos(turn.start_pos) or not plate.check_pos(turn.end_pos)):
            return False

        if (plate.get_color_map(turn.start_pos) != turn.color or
                plate.get_type_map(turn.start_pos) == plate.empty_map or
                plate.get_color_map(turn.end_pos) == turn.color):
            return False

        now_figure = plate.get_map(turn.start_pos)
        figure_type = plate.get_type_figure(now_figure)

        # pown
        if figure_type == plate.pown:
            return check.check_pown(turn, plate)

        coord_diff = mf.difference(turn.start_pos, turn.end_pos)

        # knight
        if figure_type == plate.knight:
            return check.check_knight(*coord_diff)

        # bishop
        if figure_type == plate.bishop:
            return check.check_bishop(turn, *coord_diff, plate)

        # rook
        if figure_type == plate.rook:
            return check.check_rook(turn, *coord_diff, plate)

        # king
        if figure_type == plate.king:
            if ((coord_diff[0] == 1 or coord_diff[0] == 0) and
                    (coord_diff[1] == 1 or coord_diff[1] == 0)):
                return True

        # queen
        if figure_type == plate.queen:
            return (check.check_bishop(turn, *coord_diff, plate) or
                    check.check_rook(turn, *coord_diff, plate))

        return False

    def generate_all_possible_turns(self, plate, color):
        possible_turns = defaultdict(list)
        # dict key = position of possible turn
        # dict value = list of positions where from this turn can be done

        for pos in product(range(plate.field_size), repeat=2):
            if plate.get_color_map(pos) == color:
                if plate.get_type_map(pos) == plate.pown:
                    gt.generate_turns_pown(pos, plate, possible_turns)

                if plate.get_type_map(pos) == plate.knight:
                    gt.generate_turns_knight(pos, plate, possible_turns, color)

                if plate.get_type_map(pos) == plate.rook:
                    gt.generate_turns_rook(pos, plate, possible_turns, color)

                if plate.get_type_map(pos) == plate.bishop:
                    gt.generate_turns_bishop(pos, plate, possible_turns, color)

                if plate.get_type_map(pos) == plate.queen:
                    gt.generate_turns_queen(pos, plate, possible_turns, color)

                if plate.get_type_map(pos) == plate.king:
                    gt.generate_turns_king(pos, plate, possible_turns, color)

        return possible_turns

    def thread_generate(self, plate, color, depth, turns, index, return_dict):
        best_cost = -9999 if color == plate.black else 9999
        best_turn = Turn((-1, -1), (-1, -1), 0)

        for turn in turns:
            tmp = plate.do_turn(Turn(turn[0], turn[1], color))
            now_cost = self.ai_turn(plate, 3 - color, depth - 1)[1]

            plate.do_turn(Turn(turn[1], turn[0], color), fig=tmp)

            if now_cost >= best_cost:
                best_cost = now_cost
                best_turn = Turn(turn[0], turn[1], color)

        return_dict[index] = (best_turn, best_cost)

    def root_ai_turn(self, plate, color, depth):
        manager = Manager()
        return_dict = manager.dict()

        possible_turns = self.generate_all_possible_turns(plate, color)

        best_cost = -9999 if color == plate.black else 9999
        best_turn = Turn((-1, -1), (-1, -1), 0)

        turns = []
        threads = []

        for end_pos in possible_turns:
            for start_pos in possible_turns[end_pos]:
                turns.append((start_pos, end_pos))
                self.depth[depth - 1] += 1

        av_threads = get_num_threads()
        print(av_threads, turns)

        num_of_turns = len(turns) // av_threads + 1
        num_of_threads = len(turns) // num_of_turns + 1

        for i in range(num_of_threads):
            now_plate = Field(None, plate)
            start = i * num_of_turns

            end = (i + 1) * num_of_turns
            end = end if end < len(turns) else len(turns) - 1

            threads.append(Process(target=self.thread_generate, name=len(threads),
                                   args=(now_plate, color, depth, turns[start:end + 1], i, return_dict)))

            threads[len(threads) - 1].start()

        for thread in threads:
            thread.join()

        return max(return_dict.values(), key=lambda x: x[1])

    def ai_turn(self, plate, color, depth, alpha=-10000, beta=10000):
        possible_turns = self.generate_all_possible_turns(plate, color)

        best_cost = -9999 if color == plate.black else 9999
        best_turn = Turn((-1, -1), (-1, -1), 0)

        for end_pos in possible_turns:
            for start_pos in possible_turns[end_pos]:
                self.depth[depth - 1] += 1
                tmp = plate.do_turn(Turn(start_pos, end_pos, color))

                if depth == 1:
                    now_cost = plate.calculate_plate_cost(color, self.figures_cost)
                else:
                    now_cost = self.ai_turn(plate, 3 - color, depth - 1, alpha, beta)[1]

                plate.do_turn(Turn(end_pos, start_pos, color), fig=tmp)

                if color == plate.black:
                    if now_cost >= best_cost:
                        best_cost = now_cost
                        best_turn = Turn(start_pos, end_pos, color)
                    alpha = max(alpha, best_cost)
                else:
                    if now_cost <= best_cost:
                        best_cost = now_cost
                        best_turn = Turn(start_pos, end_pos, color)
                    beta = min(beta, best_cost)

                if beta <= alpha:
                    return (best_turn, best_cost)

        return (best_turn, best_cost)
