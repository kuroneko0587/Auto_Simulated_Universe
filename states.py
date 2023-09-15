import threading
import traceback
import keyboard
import pyautogui
import cv2 as cv
import numpy as np
import time
import win32gui, win32api, win32con
import random
import sys
from copy import deepcopy
from utils.log import log, set_debug
from utils.map_log import map_log
from utils.update_map import update_map
from utils.utils import UniverseUtils, set_forground, notif
import os
from align_angle import main as align_angle
from utils.config import config
import datetime
import requests
import pytz
import pyuac
try:
    from mylib import get_direc_only_minimap, ban, isrun
except:
    from utils.mylib import get_direc_only_minimap, ban, isrun

# 版本号
version = "v5.6 gamma"


class SimulatedUniverse(UniverseUtils):
    def __init__(
        self, find, debug, show_map, speed, unlock=False, bonus=False, update=0, gui=0
    ):
        super().__init__()
        # t1 = threading.Thread(target=os.system,kwargs={'command':'notif.exe > NUL 2>&1'})
        # t2 = threading.Thread(target=os.system,kwargs={'command':'python notif.py > NUL 2>&1'})
        log.info("当前版本：" + version + "  当前命途：" + self.fate)
        if gui:
            try:
                lowest = (
                    requests.get(
                        "https://api.github.com/repos/CHNZYX/Auto_Simulated_Universe/releases/latest"
                    )
                    .json()["name"]
                    .split("lowest")[1]
                    .strip()
                    .strip("v")
                )
                log.info("版本下限：v" + lowest)
            except:
                log.info("网络异常，尝试备用网址")
                try:
                    lowest = requests.get(
                        "https://chnzyx.github.io/asu_version_check/"
                    ).text.strip()
                    log.info("版本下限：v" + lowest)
                except:
                    log.info("网络异常，强制退出")
            ves = version[1:].split(" ")[0]
            try:
                if float(lowest) > float(ves):
                    log.info("当前版本过低，强制退出")
                    self.validation = 0
                else:
                    self.validation = 1
            except:
                self.validation = 0
        else:
            self.validation = 1
        if "debug" in version and not gui:
            log.info("欢迎加入模拟宇宙小群，群号：921407322 密码：zyxxyz")
        self.now_map = None
        self.now_map_sim = None
        self.real_loc = [0, 0]
        self.debug_map = np.zeros((8192, 8192), dtype=np.uint8)
        self._stop = False
        self.img_set = []
        self.find = find
        self.debug = debug
        self.speed = speed
        self._show_map = show_map & find
        self.floor = 0
        self.count = 0
        self.count_tm = time.time()
        self.floor_tm = time.time()
        self.init_tm = time.time()
        self.my_cnt = 0
        self.re_align = 0
        self.unlock = unlock
        self.check_bonus = bonus
        self.kl = 0
        self.gui = gui
        self.fail_count = 0
        ex_notif = ""
        if not debug:
            pyautogui.FAILSAFE = False
        if bonus:
            ex_notif = " 自动领取沉浸奖励"
            log.info(ex_notif)
        self.update_count()
        notif("开始运行" + ex_notif, f"初始计数：{self.count}")
        set_debug(debug > 0)
        if update and find:
            update_map()
        self.lst_changed = time.time()
        log.info("加载地图")
        for file in os.listdir("imgs/maps"):
            pth = "imgs/maps/" + file + "/init.jpg"
            if os.path.exists(pth):
                image = cv.imread(pth)
                self.img_set.append((file, self.extract_features(image)))
                self.img_map[file]= image
        log.info("加载地图完成，共 %d 张" % len(self.img_set))

    # 初始化地图，刚进图时调用
    def init_map(self):
        self.backup_map()
        self.big_map = np.zeros((8192, 8192), dtype=np.uint8)
        self.big_map_c = 0
        self.lst_tm = 0
        self.tries = 0
        self.his_loc = (30, 30)
        self.offset = (30, 30)
        self.now_loc = (4096, 4096)
        self.mini_state = 1
        self.ang_off = 0
        self.ang_neg = 0
        self.first_mini = 1
        self.map_file = "imgs/maps/my_" + str(random.randint(0, 99999)) + "/"
        if self.find == 0 and not os.path.exists(self.map_file):
            os.mkdir(self.map_file)

    def route(self):
        self.threshold = 0.97
        self.battle = 0
        self.quit = 0
        self.floor_init = 0
        self.in_battle = 0
        self.init_map()
        fail_cnt = 0
        fail_time = 0
        self.confirm_time = 0
        self._stop = os.stat("imgs/mon" + self.tss).st_size != 141882
        while True:
            if self._stop:
                break
            hwnd = win32gui.GetForegroundWindow()  # 根据当前活动窗口获取句柄
            Text = win32gui.GetWindowText(hwnd)
            warn_game = False
            cnt = 0
            while Text != "崩坏：星穹铁道" and not self._stop:
                self.lst_changed = time.time()
                if self._stop:
                    raise KeyboardInterrupt
                if not warn_game:
                    warn_game = True
                    log.warning("等待游戏窗口")
                time.sleep(0.5)
                cnt += 1
                if cnt == 1200:
                    set_forground()
                hwnd = win32gui.GetForegroundWindow()  # 根据当前活动窗口获取句柄
                Text = win32gui.GetWindowText(hwnd)
            if self._stop:
                break
            self.get_screen()
            ban(self)
            #self.click_target('imgs/init.jpg',0.9,True) # 如果需要输出某张图片在游戏窗口中的坐标，可以用这个
            """
            if begin and not self.check("f", 0.4437,0.4231) and not self.check("abyss/1",0.8568,0.6769):
                begin = 0
                self.press("F4")
                time.sleep(0.6)
                self.get_screen()
            """
            res = self.normal()
            # 未匹配到图片，降低匹配阈值，若一直无法匹配则乱点
            if res == 0:
                if time.time()-self.confirm_time>4 and time.time()-fail_time<=7.5:
                    if self.click_text(['点击空白']):
                        time.sleep(0.5)
                    if self.ts.nothing:
                        self.in_battle = time.time()
                if time.time()-self.in_battle>7:
                    if self.threshold == 0.97 and fail_cnt==0:
                        log.info("匹配不到任何图标")
                        fail_time = time.time()
                    else:
                        time.sleep(0.8)
                    if self.threshold > 0.95:
                        self.threshold -= 0.015
                    elif time.time()-fail_time>7.5:
                        time.sleep(0.15)
                        if fail_cnt <= 1:
                            self.click((0.5000, 0.1454))
                            fail_cnt += 1
                        else:
                            self.click((0.2062, 0.2054))
                            fail_cnt = 0
                            fail_time = time.time()
                        time.sleep(0.35)
                        self.threshold = 0.97
                    time.sleep(0.1)
            # 匹配到图片 res=1时等待一段时间
            else:
                fail_cnt = 0
                self.threshold = 0.97
                fail_time = time.time()
        log.info("停止运行")

    def end_of_uni(self):
        self.update_count(0)
        self.my_cnt += 1
        tm = int((time.time() - self.init_tm) / 60)
        remain = 34 - self.count
        if remain > 0:
            remain = int(remain * (time.time() - self.init_tm) / self.my_cnt / 60)
        else:
            remain = 0
        if (
            notif(
                "已完成",
                f"计数:{self.count} 已使用：{tm//60}小时{tm%60}分钟  平均{tm//self.my_cnt}分钟一次  预计剩余{remain//60}小时{remain%60}分钟",
                cnt=str(self.count),
            )
            >= 34
            and self.debug == 0
        ):
            self._stop = 1
        ban(self)
        self.floor = 0

    def normal(self):
        # self.lst_changed：最后一次交互时间，长时间无交互则暂离
        bk_lst_changed = self.lst_changed
        self.lst_changed = time.time()
        # 战斗界面
        if self.check("c", 0.9464, 0.1287, threshold=0.985) or self.check(
            "auto_2", 0.0583, 0.0769
        ):
            # 需要打开自动战斗
            if self.check("c", 0.9464, 0.1287, threshold=0.985):
                self.press("v")
            if time.time() - self.f_time < 20:
                self.f_time = 0
                self.floor -= 1
                self.restore_map()
            # self.battle：最后一次处于战斗状态的时间，0表示处于非战斗状态
            if self.fate == "丰饶":
                if random.randint(0, 5) == 3:
                    self.press("3")
                if random.randint(0, 6) == 3:
                    self.press("r")
            self.battle = time.time()
            self.in_battle = time.time()
            return 1
        # 祝福界面/回响界面 （放在一起处理了）
        if self.check("choose_bless", 0.9266, 0.9491):
            self.battle = 0
            ok = 0
            for _ in range(12):
                self.get_screen()
                img_down = self.check("z", 0.5042, 0.3204, mask="mask", large=False)
                if (
                    self.ts.split_and_find(self.tk.fates, img_down, mode="bless")[1]
                    or self._stop
                ):
                    time.sleep(0.2)
                    break
                time.sleep(0.2)
            self.get_screen()
            img_up = self.check("z", 0.5047, 0.5491, mask="mask_bless", large=False)
            res_up = self.ts.split_and_find(self.tk.prior_bless, img_up, bless_skip=self.tk.skip)
            img_down = self.check("z", 0.5042, 0.3204, mask="mask", large=False)
            res_down = self.ts.split_and_find([self.fate], img_down, mode="bless")
            ban(self)
            if res_up[1] == 2:
                self.click(self.calc_point((0.5047, 0.5491), res_up[0]))
            elif res_down[1] == 2 and (res_up[1] != 3 or self.fate != "毁灭"):
                self.click(self.calc_point((0.5042, 0.3204), res_down[0]))
            # 未匹配到优先祝福，刷新祝福并再次匹配
            else:
                self.click((0.2990, 0.1046))
                time.sleep(0.8)
                for _ in range(8):
                    self.get_screen()
                    img_down = self.check("z", 0.5042, 0.3204, mask="mask", large=False)
                    if self.ts.split_and_find(self.tk.fates, img_down)[1] or self._stop:
                        time.sleep(0.2)
                        break
                    time.sleep(0.2)
                self.get_screen()
                img_up = self.check("z", 0.5047, 0.5491, mask="mask_bless", large=False)
                res_up = self.ts.split_and_find(self.tk.prior_bless, img_up,bless_skip=self.tk.skip)
                img_down = self.check("z", 0.5042, 0.3204, mask="mask", large=False)
                res_down = self.ts.split_and_find(
                    self.tk.secondary, img_down, mode="bless"
                )
                if res_up[1] >= 2:
                    self.click(self.calc_point((0.5047, 0.5491), res_up[0]))
                else:
                    self.click(self.calc_point((0.5042, 0.3204), res_down[0]))
            self.click((0.1203, 0.1093))
            time.sleep(1.8)
            self.confirm_time = time.time()
            return 1
        # F交互界面
        elif self.check("f", 0.4443, 0.4417, mask="mask_f1"):
            # is_killed：是否是禁用交互（沉浸奖励、复活装置、下载装置）
            is_killed = 0
            time.sleep(0.4)
            self.get_screen()
            if self.check("f", 0.4443, 0.4417, mask="mask_f1"):
                for _ in range(4):
                    img = self.check("z", 0.3344, 0.4241, mask="mask_f", large=False)
                    text = self.ts.sim_list(self.tk.interacts, img)
                    if text is None:
                        img = self.check(
                            "z", 0.3365, 0.4231, mask="mask_f", large=False
                        )
                        text = self.ts.sim_list(self.tk.interacts, img)
                    if text is not None:
                        break
                    time.sleep(0.3)
                    self.get_screen()
                # 黑塔
                if self.ts.sim("黑塔"):
                    # 与黑塔交互后30秒内禁止再次交互（防止死循环）
                    if time.time() - self.quit > 30 and self.floor:
                        self.quit = time.time()
                        self.press(self.hotkey)
                        self.battle = 0
                    else:
                        is_killed = 1
                else:
                    # tele：区域-xx  exit：离开模拟宇宙
                    if self.ts.sim("区域"):
                        log.info(f"识别到传送点")
                        self.press(self.hotkey)
                        time.sleep(1)
                        self.get_screen()
                        img = self.check(
                            "z", 0.3182, 0.4333, mask="mask_f", large=False
                        )
                        if self.ts.sim("区域", img):
                            return 0
                        else:
                            self.init_map()
                            self.floor += 1
                            self.f_time = time.time()
                            map_log.info(
                                f"地图{self.now_map}已完成,相似度{self.now_map_sim},进入{self.floor+1}层"
                            )
                            return 1
                    elif self.re_align == 1 and self.debug == 0:
                        # align_angle(10, 1)
                        # self.multi = config.multi
                        self.re_align += 1
                    is_killed = text in ["沉浸", "紧锁", "复活", "下载"]
                    if is_killed == 0:
                        self.press(self.hotkey)
                    self.battle = 0
                if is_killed == 0:
                    return 1
        # 跑图状态
        if isrun(self):
            if self.floor_init == 0:
                self.get_level()
                self.floor_init = 1
            self.lst_changed = bk_lst_changed
            self.battle = 0
            # 刚进图，初始化一些数据
            if self.big_map_c == 0:
                pyautogui.keyUp("w")
                # 黑屏检测
                while 1:
                    men = np.mean(self.get_screen())
                    if men > 12:
                        break
                    time.sleep(0.1)
                    if self._stop:
                        return 1
                if self._stop:
                    return 1
                self.big_map_c = 1
                # 寻路模式，匹配最接近的地图
                if self.find:
                    now_time = time.time()
                    self.now_map_sim = -1
                    self.now_map = -1
                    if self.floor in [0, 5]:
                        self.mini_state = 0
                        self.stop_move = 0
                        while True:
                            self.exist_minimap()
                            now_map, now_map_sim = self.match_scr(self.loc_scr)
                            if self.now_map_sim < now_map_sim:
                                self.now_map, self.now_map_sim = now_map, now_map_sim
                            if (
                                (self.now_map_sim > 0.65 or time.time() - now_time > 2.5)
                                and self.now_map_sim != -1
                            ) or self._stop:
                                break
                        log.info(f"地图编号：{self.now_map}  相似度：{self.now_map_sim}")
                        if self.now_map_sim < 0.35:
                            notif("相似度过低", "疑似在黑塔办公室")
                            if self.debug==2:
                                time.sleep(10000)
                            # self.init_map()
                            # return 1
                        if self.debug == 2:
                            try:
                                with open(
                                    "check0.txt",
                                    "r",
                                    encoding="utf-8",
                                    errors="ignore",
                                ) as fh:
                                    s = fh.readline().strip("\n")
                                s = eval(s)
                                self.kl = 0
                                if not self.now_map in s:
                                    s.append(self.now_map)
                                    notif(f"地图编号：{self.now_map}",f"相似度：{self.now_map_sim}")
                                else:
                                    #self.kl = 1
                                    pass
                                with open(
                                    "check0.txt",
                                    "w",
                                    encoding="utf-8",
                                ) as fh:
                                    fh.write(str(s))
                            except:
                                pass
                        self.now_pth = "imgs/maps/" + self.now_map + "/"
                        files = self.find_latest_modified_file(self.now_pth)
                        print("地图文件：", files)
                        self.big_map = cv.imread(files, cv.IMREAD_GRAYSCALE)
                        self.debug_map = deepcopy(self.big_map)
                        xy = files.split("/")[-1].split("_")[1:3]
                        self.now_loc = (4096 - int(xy[0]), 4096 - int(xy[1]))
                        self.target = self.get_target(self.now_pth + "target.jpg")
                        self.get_screen()
                        shape = (int(self.scx * 190), int(self.scx * 190))
                        local_screen = self.get_local(0.9333, 0.8657, shape)
                        self.init_ang = 360 - self.get_now_direc(local_screen) - 90
                        log.info("target %s" % self.target)
                    if self._stop:
                        return 1
                    self.press("1")
                # 录制模式，保存初始小地图
                else:
                    time.sleep(3)
                    self.mini_state = 0
                    self.exist_minimap()
                    cv.imwrite(self.map_file + "init.jpg", self.loc_scr)
            self.get_screen()
            if time.time() - self.lst_tm > 5 and self.mini_state == 0:
                if self.find == 0:
                    self.press("s", 0.5)
                    if self._stop == 0:
                        pyautogui.keyDown("w")
                    time.sleep(0.5)
                    self.get_screen()
            self.lst_tm = time.time()
            
            # self.kl |= self.floor >= 6 and self.debug == 2
            # 长时间未交互/战斗，暂离或重开
            if (
                (
                    (time.time() - self.lst_changed >= 45 - 7 * self.debug)
                    and self.find == 1
                )
                or (self.floor == 12 and self.mini_state > 4)
                or self.kl
            ):
                time.sleep(2.5)
                self.press("esc")
                time.sleep(2)
                self.init_map()
                self.floor_init = 0
                if self.floor == 12 or self.kl:
                    self.end_of_uni()
                    self.click((0.2708, 0.1324))
                    log.info(f"通关！当前层数:{self.floor+1}")
                elif self.debug == 2:
                    map_log.error(f"地图{self.now_map}出现问题,退出程序")
                    notif(f"地图{self.now_map}出现问题,退出程序", "DEBUG")
                    self._stop = 1
                elif self.fail_count <= 1:
                    notif("暂离", f"地图{self.now_map}，当前层数:{self.floor+1}")
                    map_log.error(f"地图{self.now_map}未发现目标,相似度{self.now_map_sim}，尝试暂离")
                    self.re_align += 1
                    self.fail_count += 1
                else:
                    self.multi = 1.01
                    if self.debug == 0:
                        notif("中途结算", f"地图{self.now_map}，当前层数:{self.floor+1}")
                        self.floor = 0
                        self.click((0.2708, 0.1324))
                        map_log.error(
                            f"地图{self.now_map}未发现目标,相似度{self.now_map_sim}，尝试退出重进"
                        )
                        self.fail_count = 0
                    else:
                        self.re_align += 1
                        map_log.error(
                            f"地图{self.now_map}未发现目标,相似度{self.now_map_sim}，尝试暂离 DEBUG"
                        )
                self.lst_changed = time.time()
                return 1
            if self.multi == 1.01:
                align_angle(0, 1, [1], self)
            # 寻路
            if self.mini_state:
                get_direc_only_minimap(self)
            else:
                self.get_direc()
            return 2
        elif self.check("init", 0.9073,0.8435):
            self.click((0.3448, 0.4926))
            self.init_map()
        elif self.check("begin", 0.3328, 0.8148):
            con = self.check("conti", 0.1099, 0.0972)
            if not con:
                self.click((0.9375, 0.8565 - 0.1 * (self.diffi - 1)))
            self.click((0.1083, 0.1009))
            if con:
                self.get_level()
            else:
                self.floor = 0
            self.floor_init = 1
        elif self.check("start", 0.6594, 0.8389):
            self.fail_count = 0
            if self.check("team4", 0.5797, 0.2389):
                dx = 0.9266 - 0.8552
                dy = 0.8194 - 0.6741
                for i in self.order:
                    self.click(
                        (0.9266 - dx * ((i - 1) % 3), 0.8194 - dy * ((i - 1) // 3))
                    )
                    time.sleep(0.3)
            self.click((0.1635, 0.1056))
        elif self.check("fate_2", 0.1797, 0.1009):
            self.click((0.1797, 0.1009))
            self.confirm_time = time.time()
        elif self.check("fate", 0.9458, 0.9481):
            time.sleep(0.6)
            self.get_screen()
            img = self.check("z", 0.4969, 0.3750, mask="mask_fate", large=False)
            res = self.ts.split_and_find([self.fate], img)
            self.click(self.calc_point((0.4969, 0.3750), res[0]))
        elif self.check("fate_3", 0.9422, 0.9472):
            self.click((0.5047, 0.4917))
            self.click((0.5062, 0.1065))
        # 事件界面
        elif self.check("event", 0.9479, 0.9565):
            # 事件界面：选择
            if self.check("arrow", 0.1828, 0.5000, mask="mask_event"):
                self.click((self.tx, self.ty))
            # 事件界面：退出
            elif self.check("arrow_1", 0.1828, 0.5000, mask="mask_event"):
                self.click((self.tx, self.ty))
            # 事件选择界面
            elif self.check("star", 0.1828, 0.5000, mask="mask_event", threshold=0.965):
                tx, ty = self.tx, self.ty
                try:
                    import yaml
                    with open("info.yml", "r", encoding="utf-8", errors="ignore") as f:
                        event_prior = yaml.safe_load(f)["prior"]["事件"]
                except:
                    event_prior = [
                        '购买一个',
                        '丢下雕像',
                        '和序列扑满玩',
                        '信仰星神',
                        '克里珀的恩赐',
                        '哈克的藏品',
                        '动作片',
                        '感恩克里珀星神',
                        '换取1个星祝福',
                        '星神的记载',
                        '翻开牌',
                        '摧毁黑匣',
                        '1个1星祝福',
                        '1个1-星祝福',
                        '选择里奥'
                    ]
                event_prior = [self.fate] + event_prior + self.tk.secondary[1:] + ['存护','巡猎']
                self.click_text(event_prior)
                time.sleep(0.3)
                self.get_screen()
                if self.check("confirm", 0.1828, 0.5000, mask="mask_event"):
                    self.click((self.tx, self.ty))
                else:
                    self.click((tx, ty))
                    time.sleep(0.3)
                    self.click((0.1167, ty - 0.4685 + 0.3546))
                time.sleep(1)
            else:
                self.click((0.9479, 0.9565))
        # 选取奇物
        elif self.check("strange", 0.9417, 0.9481):
            img = self.check("z", 0.5000, 0.7333, mask="mask_strange", large=False)
            res = self.ts.split_and_find(self.tk.strange, img, mode="strange")
            self.click(self.calc_point((0.5000, 0.7333), res[0]))
            self.click((0.1365, 0.1093))
            self.confirm_time = time.time()
        # 丢弃奇物
        elif self.check("drop", 0.9406, 0.9491):
            self.click((0.4714, 0.5500))
            self.click((0.1339, 0.1028))
            self.confirm_time = time.time()
        elif self.check("drop_bless", 0.9417, 0.9481, threshold=0.95):
            time.sleep(1.5)
            if self.debug==2:
                time.sleep(100000)
            st = set(self.tk.fates) - set(self.tk.secondary)
            clicked = 0
            for ft in self.tk.secondary[::-1]:
                if ft != self.fate:
                    self.get_screen()
                    img_down = self.check("z", 0.5042, 0.3204, mask="mask", large=False)
                    if self.debug==2:
                        print(list(st))
                    res_down = self.ts.split_and_find(list(st), img_down, mode="bless")
                    if res_down[1] == 2:
                        self.click(self.calc_point((0.5042, 0.3204), res_down[0]))
                        clicked = 1
                        break
                    st.add(ft)
            if not clicked:
                self.click((0.4714, 0.5500))
            time.sleep(0.5)
            self.click((0.1203, 0.1093))
            self.confirm_time = time.time()
        elif self.check("setting", 0.9734, 0.3009, threshold=0.98):
            self.click((0.9734, 0.3009))
            time.sleep(2)
            self.click((0.3505,0.9398))
            time.sleep(2)
            self.click_text(["战斗功能"])
            for _ in range(5):
                pyautogui.scroll(-1)
                time.sleep(0.1)
            time.sleep(0.3)
            self.click_text(["脱离卡死"])
        elif self.check("enhance", 0.9208, 0.9380):
            self.quit = time.time()
            time.sleep(1.5)
            for i in [None, (0.7984, 0.6824), (0.6859, 0.6824)]:
                self.get_screen()
                if self.check("enhance_fail", 0.1068, 0.0907):
                    break
                if i is not None:
                    self.click(i)
                    time.sleep(0.3)
                self.click((0.1089, 0.0926))
                time.sleep(0.3)
                tm = time.time()
                self.get_screen()
                while not self.check("enhance", 0.9208, 0.9380) and time.time()-tm<7:
                    self.click((0.2062, 0.2054))
                    time.sleep(0.3)
                    self.get_screen()
            self.press("esc")
            time.sleep(1.8)
            self.confirm_time = time.time()
            if self.floor >= 12:
                self.floor = 11
        elif self.check("yes1", 0.5, 0.5, mask="mask_end"):
            self.click((self.tx,self.ty))
            return 1
        else:
            return 0
        return 1

    def find_latest_modified_file(self, folder_path):
        files = [
            os.path.join(folder_path, file)
            for file in os.listdir(folder_path)
            if file.split("/")[-1][0] == "m"
        ]
        nx, ny = 4096, 4096
        file = ""
        for i in files:
            try:
                x, y = i.split("_")[-3:-1]
                x, y = int(x), int(y)
                if x < nx or y < ny:
                    nx, ny = x, y
                    file = i
            except:
                pass
        return file

    def update_count(self, read=True):
        file_name = "logs/notif.txt"
        if read:
            new_cnt = 0
            if os.path.exists(file_name):
                time_cnt = os.path.getmtime(file_name)
                with open(file_name, "r", encoding="utf-8", errors="ignore") as fh:
                    s = fh.readlines()
                    try:
                        new_cnt = int(s[0].strip("\n"))
                        time_cnt = float(s[3].strip("\n"))
                    except:
                        pass
            else:
                os.makedirs("logs", exist_ok=1)
                with open(file_name, "w", encoding="utf-8") as file:
                    file.write("0")
                    file.close()
                time_cnt = os.path.getmtime(file_name)
        else:
            new_cnt = self.count + 1
            time_cnt = self.count_tm
        dt = datetime.datetime.now().astimezone()
        """
        America: GMT-5
        Asia: GMT+8
        Europe: GMT+1
        TW, HK, MO: GMT+8
        """
        tz_info = None
        try:
            tz_dict = {
                "Default": None,
                "America": pytz.timezone("US/Central"),
                "Asia": pytz.timezone("Asia/Shanghai"),
                "Europe": pytz.timezone("Europe/London"),
            }
            tz_info = tz_dict[config.timezone]
        except:
            pass

        # convert to server time
        dt = dt.astimezone(tz_info)
        current_weekday = dt.weekday()
        monday = dt + datetime.timedelta(days=-current_weekday)
        target_datetime = datetime.datetime(
            monday.year, monday.month, monday.day, 4, 0, 0, tzinfo=tz_info
        )
        monday_ts = target_datetime.timestamp()
        if dt.timestamp() >= monday_ts and time_cnt < monday_ts:
            self.count = int(not read)
        else:
            self.count = new_cnt
        self.count_tm = time.time()

    def del_pt(self, img, A, S, f):
        if (
            A[0] < 0
            or A[1] < 0
            or A[0] >= img.shape[0]
            or A[1] >= img.shape[1]
            or (img[A] == [0, 0, 0]).all()
            or (not f(img[A]) and self.get_dis(A, S) > 5)
            or self.get_dis(A, S) > 10
        ):
            return
        else:
            img[A] = [0, 0, 0]
        for dx, dy in [(0, -1), (0, 1), (1, 0), (-1, 0)]:
            self.del_pt(img, (A[0] + dx, A[1] + dy), S, f)

    def get_target(self, pth):
        img = cv.imread(pth)
        res = set()
        f_set = [
            lambda p: p[2] < 85 and p[1] < 85 and p[0] > 180,  # 路径点 蓝
            lambda p: p[2] > 180 and p[1] < 70 and p[0] < 70,  # 怪 红
            lambda p: p[2] < 90 and p[1] > 150 and p[0] < 90,  # 交互点 绿
            lambda p: p[2] > 180 and p[1] > 180 and p[0] < 70,  # 终点 黄
        ]
        for i in range(img.shape[0]):
            for j in range(img.shape[1]):
                for k in range(4):
                    if f_set[k](img[i, j]):
                        p = self.get_center(img, i, j)
                        res.add((p, k))
                        p = (int(p[0]), int(p[1]))
                        self.del_pt(img, p, p, f_set[k])
                        if k == 3:
                            self.last = p
        # cv.imwrite("imgs/tmp1.jpg", img)
        if self.speed:
            dis = 1000000
            pt = None
            for i in res:
                if i[1] == 1 and self.get_dis(i[0], self.last) < dis:
                    dis = self.get_dis(i[0], self.last)
                    pt = i
            for i in deepcopy(res):
                if i[1] == 1 and pt != i:
                    res.remove(i)
                    res.add((i[0], 0))
        return res

    def get_center(self, img, i, j):
        rx, ry, rt = 0, 0, 0
        for x in range(-7, 7):
            for y in range(-7, 7):
                if (
                    i + x >= 0
                    and j + y >= 0
                    and i + x < img.shape[0]
                    and j + y < img.shape[1]
                ):
                    s = np.sum(img[i + x, j + y])
                    if s > 30 and s < 255 * 3 - 30:
                        rt += 1
                        rx += x
                        ry += y
        return (i + rx / rt, j + ry / rt)
    
    def backup_map(self):
        try:
            self.bbig_map,self.bbig_map_c,self.blst_tm,self.btries,self.bhis_loc,self.boffset,self.bnow_loc,self.bmini_state,self.bang_off,self.bang_neg,self.bfirst_mini=self.big_map,self.big_map_c,self.lst_tm,self.tries,self.his_loc,self.offset,self.now_loc,self.mini_state,self.ang_off,self.ang_neg,self.first_mini
        except:
            pass
    def restore_map(self):
        self.big_map,self.big_map_c,self.lst_tm,self.tries,self.his_loc,self.offset,self.now_loc,self.mini_state,self.ang_off,self.ang_neg,self.first_mini=self.bbig_map,self.bbig_map_c,self.blst_tm,self.btries,self.bhis_loc,self.boffset,self.bnow_loc,self.bmini_state,self.bang_off,self.bang_neg,self.bfirst_mini


    def stop(self, *_, **__):
        log.info("尝试停止运行")
        self._stop = True

    def on_key_press(self, event):
        global stop_flag
        if event.name == "f8":
            print("F8 已被按下，尝试停止运行")
            self.stop()

    def show_map(self):
        # Create a window to display the image
        cv.namedWindow("Map", cv.WINDOW_AUTOSIZE)

        # Update the image every second
        while not self._stop:
            if self.debug_map.shape[0] == 8192:
                continue
            # Load the updated image
            updated_image = self.debug_map.copy()

            # 灰度图转RGB
            updated_image = cv.cvtColor(updated_image, cv.COLOR_GRAY2RGB)
            updated_image[
                self.real_loc[0] - 2 : self.real_loc[0] + 3,
                self.real_loc[1] - 2 : self.real_loc[1] + 3,
            ] = [49, 49, 140]

            # 将图片放大两倍
            updated_image = cv.resize(
                updated_image, None, fx=2, fy=2, interpolation=cv.INTER_LINEAR
            )

            # Update the displayed image
            cv.imshow("Map", updated_image)

            # Wait for one second
            cv.waitKey(1000)

        # Destroy the window
        cv.destroyAllWindows()

    def check_req(self):
        self._stop = os.system("pip show numpy > NUL 2>&1") and not self.unlock
        if self._stop:
            log.info("未安装依赖库或环境变量未正确设置")
        time.sleep(10)
        self._stop = os.system("pip show numpy > NUL 2>&1") and not self.unlock
        if self._stop:
            log.info("未安装依赖库或环境变量未正确设置")

    def start(self):
        self._stop = False
        if self.validation == 0:
            return
        keyboard.on_press(self.on_key_press)
        if self._show_map:
            t_map = threading.Thread(target=self.show_map)
            t_map.start()
        threading.Thread(target=self.check_req).start()
        try:
            self.route()
        except KeyboardInterrupt:
            print("KeyboardInterrupt")
            if not self._stop:
                self.stop()


def main():
    log.info(f"find: {find}, debug: {debug}, show_map: {show_map}")
    su = SimulatedUniverse(find, debug, show_map, speed, bonus=bonus, update=update)
    try:
        su.start()
    except Exception:
        traceback.print_exc()
    finally:
        su.stop()


if __name__ == "__main__":
    if not pyuac.isUserAdmin():
        pyuac.runAsAdmin()
    else:
        find = 1
        debug = 0
        show_map = 0
        update = 0
        speed = 0
        bonus = 0
        for i in sys.argv[1:]:
            st = i.split("-")[-1]
            if "=" not in st:
                st = st + "=1"
            exec(st)
        main()
