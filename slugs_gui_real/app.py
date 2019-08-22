import sys
from PyQt5.Qt import *
from gridworld import *
import copy
import itertools
import write_structured_slugs
import compute_all_vis
import cv2


class MainWindow(QMainWindow):
    enter_safety = None
    enter_liveness = None
    enter_target_reachability = None
    enter_sensor_uncertainty = None
    num_agents = 0
    num_targets = 0
    image_dialog = None
    agent_list = []
    target_list = []
    current_agent = None

    def __init__(self, *args):
        QMainWindow.__init__(self, *args)
        self.setFixedSize(800, 250)
        self.image_select = QLabel(self)
        self.image_select.setText("Select an image file to use: ")
        self.image_select.show()
        self.num_states_in_partition = 0
        self.current_partition_size = 0
        self.browse_button = QPushButton("Browse", self)
        self.is_partition_selection = False
        layout = QHBoxLayout(self)
        layout.addWidget(self.image_select)
        layout.addWidget(self.browse_button)
        group = QGroupBox(self)
        group.setLayout(layout)
        group.setGeometry(0, -25, 650, 200)
        self.browse_button.clicked.connect(self.browseButtonClicked)
        self.sensor_uncertainty = 1
        self.belief_safety = 0
        self.belief_liveness = 0
        self.target_reachability = ""
        self.num_agents = 0

    def browseButtonClicked(self):
        self.browse_button.close()
        self.image_select.close()
        self.close()
        self.imagePath = QFileDialog.getOpenFileName(self, "Open File", "", "Images (*.png *.jpg *.pgm)")
        self.imageObject = QImage()
        self.imageObject.load(self.imagePath[0])
        self.new_height = self.imageObject.height() if self.imageObject.height() > 1000 else 1000
        self.new_width = self.imageObject.width() if self.imageObject.width() > 1000 else 1000
        self.new_height = self.new_height if self.new_height < 1500 else 1500
        self.resized_image = self.imageObject.scaled(self.new_width, self.new_height)
        image = QPixmap.fromImage(self.resized_image)
        scene = QGraphicsScene(self)
        scene.addPixmap(image)
        self.show()
        self.view = QGraphicsView(self)

        self.view.setGeometry(0, 0, self.new_width, self.new_height)
        self.view.setScene(scene)
        self.view.show()
        self.setFixedSize(self.new_width, self.new_height + self.new_height/4)
        self.enter_rows = QLineEdit()
        self.enter_cols = QLineEdit()
        self.submit_button = QPushButton("Submit dimensions", self)
        self.enter_rows.setPlaceholderText("Number of rows")
        self.enter_cols.setPlaceholderText("Number of cols")
        layout = QVBoxLayout()
        layout.addWidget(self.enter_rows)
        layout.addWidget(self.enter_cols)
        layout.addWidget(self.submit_button)
        group = QGroupBox(self)
        group.setLayout(layout)
        group.setGeometry(0, self.new_height, self.new_width, self.new_height/4)
        group.show()
        self.submit_button.clicked.connect(self.slotDimensionsEntered)

    def slotDimensionsEntered(self):
        try:
            self.c = int(self.enter_cols.text())
            self.r = int(self.enter_rows.text())
        except ValueError:
            message_box = QMessageBox()
            message_box.warning(self, "Error",
                                "Please input an integer for each field")
        else:
            self.enter_cols.close()
            self.enter_rows.close()
            self.submit_button.close()
            count = self.r * self.c - 1
            width = self.resized_image.width() / self.c
            height = self.resized_image.height() / self.r
            self.buttons = {}
            if self.r * self.c - 1 < 1000:
                width = width if width > 60 else 60.0

            else:
                width = width if width > 70 else 70.0
            height = height if height > 50 else 50.0
            print(self.resized_image.width(), self.resized_image.height())
            self.resized_image = self.imageObject.scaled(width * self.c, height * self.r)
            print(self.resized_image.width(), self.resized_image.height())
            image = QPixmap.fromImage(self.resized_image)
            scene = QGraphicsScene(self)
            scene.addPixmap(image)
            self.view = QGraphicsView(self)
            self.view.setGeometry(0, 0, self.resized_image.width(), self.resized_image.height())
            self.view.setScene(scene)
            self.view.show()
            self.setFixedSize(self.resized_image.width(), self.resized_image.height() + 100)
            for i in range(self.r):
                for j in range(self.c):
                    s = str(count)
                    self.buttons[count] = QPushButton(s, self)
                    self.buttons[count].setCheckable(True)
                    button_palette = QPalette()
                    button_palette.setColor(QPalette.ButtonText, Qt.black)
                    button_palette.setColor(QPalette.Background, Qt.transparent)
                    button_palette.setColor(QPalette.Window, Qt.transparent)
                    self.buttons[count].setPalette(button_palette)
                    self.buttons[count].setGeometry((self.c - j - 1) * width, i * height, width, height)
                    self.buttons[count].setFlat(True)
                    self.buttons[count].show()
                    self.buttons[count].clicked.connect(self.slotDoNothing)
                    count -= 1
            self.displayAddAgent()

    def displayAddAgent(self):
        self.add_agent_button = QPushButton("Add Agent " + str(len(self.agent_list)), self)
        self.add_agent_button.setGeometry(0, self.resized_image.height(), self.resized_image.width(),
                                          50)
        self.add_agent_button.show()
        self.add_agent_button.clicked.connect(self.slotAgentButtonClicked)
        self.finish_adding_agents = QPushButton("Finish Adding Agents", self)
        self.finish_adding_agents.setGeometry(0, self.resized_image.height() + 50,
                                              self.resized_image.width(),
                                              50)
        self.finish_adding_agents.show()
        self.finish_adding_agents.clicked.connect(self.slotFinishAddingAgents)

    def slotFinishAddingAgents(self):
        self.finish_adding_agents.hide()
        self.add_agent_button.hide()
        #self.finish_adding_agents.deleteLater()
        #self.add_agent_button.deleteLater()
        self.is_partition_selection = False
        self.add_target_button = QPushButton("Add Target " + str(len(self.target_list)), self)
        self.add_target_button.setGeometry(0, self.resized_image.height(), self.resized_image.width(),
                                          50)
        self.add_target_button.show()
        self.add_target_button.clicked.connect(self.slotTargetButtonClicked)
        self.finish_adding_targets = QPushButton("Finish Adding Targets", self)
        self.finish_adding_targets.setGeometry(0, self.resized_image.height() + 50,
                                              self.resized_image.width(),
                                              50)
        self.finish_adding_targets.show()
        self.finish_adding_targets.clicked.connect(self.slotFinishButtonClicked)

    def slotDoNothing(self):
        self.sender().setChecked(False)

    def slotTargetButtonClicked(self):
        target_window = AddWindow("target", self)
        target_window.show()

    def slotAgentButtonClicked(self):
        agent_window = AddWindow("agent", self)
        self.is_partition_selection = True
        agent_window.show()

    def addTarget(self, target):
        assert isinstance(target, Target)
        print(target.initial_state)
        self.target_list.append(target)
        self.num_targets += 1
        self.add_agent_button.hide()
        self.initial_state_button = QPushButton("Enter Target " + str(len(self.target_list) - 1) + "'s initial state",
                                                self)
        self.initial_state_button.setGeometry(0, self.resized_image.height(), self.resized_image.width(),
                                              100)
        self.initial_state_button.show()
        self.current_target = target
        count = self.r * self.c - 1
        width = self.resized_image.width() / self.c
        height = self.resized_image.height() / self.r

        for i in range(self.r):
            for j in range(self.c):
                self.buttons[count].close()
                s = str(count)
                self.buttons[count] = QPushButton(s, self)
                self.buttons[count].setCheckable(True)
                button_palette = QPalette()
                button_palette.setColor(QPalette.ButtonText, Qt.black)
                button_palette.setColor(QPalette.Background, Qt.transparent)
                button_palette.setColor(QPalette.Window, Qt.transparent)
                self.buttons[count].setPalette(button_palette)
                self.buttons[count].setGeometry((self.c - j - 1) * width, i * height, width, height)
                self.buttons[count].setFlat(True)
                self.buttons[count].show()
                self.buttons[count].clicked.connect(self.slotInitialStateTarget)
                count -= 1

    def slotInitialStateTarget(self):
        agent_target_list = self.agent_list + self.target_list
        initial_state_list = [i.initial_state for i in agent_target_list]
        if int(self.sender().text()) in initial_state_list:
            message_box = QMessageBox()
            message_box.warning(self, "Error",
                                "State is already being used as an initial state")
            self.sender().setChecked(False)
            return
        else:
            self.current_target.initial_state = int(self.sender().text())
            new_palette = QPalette()
            new_palette.setColor(QPalette.ButtonText, Qt.green)
            new_palette.setColor(QPalette.Background, Qt.transparent)
            new_palette.setColor(QPalette.Window, Qt.transparent)
            self.sender().setPalette(new_palette)
            self.sender().setFlat(True)
            self.sender().setChecked(False)
        self.initial_state_button.close()
        self.add_target_button.setText("Add Target " + str(len(self.target_list)))
        for i in range(self.r * self.c):
            self.buttons[i].clicked.disconnect()
            self.buttons[i].clicked.connect(self.slotDoNothing)

    def addAgent(self, agent):
        assert isinstance(agent, Agent)
        self.agent_list.append(agent)
        self.num_agents += 1
        self.add_agent_button.hide()
        self.initial_state_button = QPushButton("Enter Agent " + str(len(self.agent_list) - 1) + "'s initial state",
                                                self)
        self.initial_state_button.setGeometry(0, self.resized_image.height(), self.resized_image.width(),
                                              100)
        self.initial_state_button.show()
        self.current_agent = agent
        count = self.r * self.c - 1
        width = self.resized_image.width() / self.c
        height = self.resized_image.height() / self.r
        for i in range(self.r):
            for j in range(self.c):
                self.buttons[count].close()
                s = str(count)
                self.buttons[count] = QPushButton(s, self)
                self.buttons[count].setCheckable(True)
                button_palette = QPalette()
                button_palette.setColor(QPalette.ButtonText, Qt.black)
                button_palette.setColor(QPalette.Background, Qt.transparent)
                button_palette.setColor(QPalette.Window, Qt.transparent)
                self.buttons[count].setPalette(button_palette)
                self.buttons[count].setGeometry((self.c - j - 1) * width, i * height, width, height)
                self.buttons[count].setFlat(True)
                self.buttons[count].show()
                self.buttons[count].clicked.connect(self.slotInitialState)
                count -= 1

    def slotInitialState(self):
        print("initial state slot")
        initial_state_list = [i.initial_state for i in self.agent_list]
        if int(self.sender().text()) in initial_state_list:
            message_box = QMessageBox()
            message_box.warning(self, "Error",
                                "State is already being used as another agent's initial state")
            self.sender().setChecked(False)
        else:
            self.current_agent.initial_state = int(self.sender().text())
            self.current_agent.allowed_states.clear()
            self.current_agent.allowed_states.append(int(self.sender().text()))
            self.initial_state_button.hide()
            new_palette = QPalette()
            new_palette.setColor(QPalette.ButtonText, Qt.green)
            new_palette.setColor(QPalette.Background, Qt.transparent)
            new_palette.setColor(QPalette.Window, Qt.transparent)
            self.sender().setPalette(new_palette)
            self.sender().setFlat(True)
            self.sender().setChecked(False)
            #Begin inputting partitions
            self.current_agent.partitions.append([])
            count = self.r * self.c - 1
            self.width = self.resized_image.width() / self.c
            self.height = self.resized_image.height() / self.r
            for i in range(self.r):
                for j in range(self.c):
                    self.buttons[count].clicked.disconnect()
                    self.buttons[count].close()
                    self.buttons[count] = QLabel(str(count), self)
                    self.buttons[count].setGeometry((self.c - j - 1) * self.width, i * self.height, self.width, self.height)
                    self.buttons[count].setAlignment(Qt.AlignCenter)
                    self.buttons[count].show()
                    count -= 1
            self.is_partition_selection = True
            self.rubberband = QRubberBand(
                QRubberBand.Rectangle, self)
            self.setMouseTracking(True)

            self.enter_partition_button = QPushButton("Enter Partition 0", self)
            self.enter_partition_button.setGeometry(0, self.resized_image.height(), self.resized_image.width(),
                                                  50)
            self.finish_entering_partitions = QPushButton(
                "Finish entering partitions for Agent " + str(len(self.agent_list) - 1), self)
            self.finish_entering_partitions.clicked.connect(self.slotFinishEntering)
            self.finish_entering_partitions.setGeometry(0, self.resized_image.height() + 50, self.resized_image.width(),
                                                    50)
            self.finish_entering_partitions.show()
            self.enter_partition_button.show()
            self.default_partition_button = QPushButton("Use default partitions and allowed states", self)
            self.default_partition_button.setGeometry(0, self.resized_image.height() + 50, self.resized_image.width(),
                                                    50)
            self.default_partition_button.clicked.connect(self.slotDefaultPartition)
            self.default_partition_button.show()
            self.enter_partition_button.clicked.connect(self.slotPartitionFinish)

    def slotDefaultPartition(self):
        self.current_agent.partitions[0] = [i for i in range(self.r * self.c)]
        print(self.current_agent.partitions)
        self.slotFinishEntering()

    def slotPartitionFinish(self):
        print("slot partition finish")
        for i in self.current_agent.partitions[len(self.current_agent.partitions) - 1]:
            self.buttons[i].setStyleSheet("QLabel {background-color : transparent; color : red; }")
        self.current_agent.partitions.append([])
        self.default_partition_button.close()
        self.enter_partition_button.setText("Enter Partition " + str(len(self.current_agent.partitions) - 1))

    def slotFinishEntering(self):
        self.finish_target_states = QPushButton("Finish Entering Target States", self)
        self.finish_target_states.setGeometry(0, self.resized_image.height(),
                                              self.resized_image.width(),
                                              100)
        self.finish_target_states.show()
        self.finish_target_states.clicked.connect(self.slotFinishTargetStates)
        count = self.r * self.c - 1
        for i in range(self.r):
            for j in range(self.c):
                self.buttons[count].close()
                s = str(count)
                self.buttons[count] = QPushButton(s, self)
                self.buttons[count].setCheckable(True)
                button_palette = QPalette()
                button_palette.setColor(QPalette.ButtonText, Qt.black)
                button_palette.setColor(QPalette.Background, Qt.transparent)
                button_palette.setColor(QPalette.Window, Qt.transparent)
                self.buttons[count].setPalette(button_palette)
                self.buttons[count].setGeometry((self.c - j - 1) * self.width, i * self.height, self.width, self.height)
                self.buttons[count].setFlat(True)
                self.buttons[count].show()
                self.buttons[count].clicked.connect(self.slotTargetState)
                count -= 1

    def slotTargetState(self):
        self.sender().setStyleSheet("QPushButton { color : blue; }")
        self.current_agent.target_states.append(int(self.sender().text()))

    def slotFinishTargetStates(self):
        for i in range(self.r * self.c):
            self.buttons[i].setStyleSheet("QLabel { color : black; }")
        self.is_partition_selection = False
        self.displayAddAgent()

    def slotAddToPartition(self):
        state = int(self.sender().text())
        current_partition_list = self.current_agent.partitions[len(self.current_agent.partitions) - 1]
        new_palette = QPalette()
        new_palette.setColor(QPalette.Background, Qt.transparent)
        new_palette.setColor(QPalette.Window, Qt.transparent)
        for i in range(len(self.current_agent.partitions) - 1):
            for j in range(len(self.current_agent.partitions[i])):
                if self.current_agent.partitions[i][j] == state:
                    message_box = QMessageBox()
                    message_box.warning(self, "Error",
                                        "State is already in a partition")
                    self.sender().setChecked(False)
                    return

        if state not in current_partition_list:
            current_partition_list.append(state)
            new_palette.setColor(QPalette.ButtonText, Qt.red)
            self.sender().setPalette(new_palette)
            self.sender().setChecked(False)
        else:
            current_partition_list.remove(state)
            new_palette.setColor(QPalette.ButtonText, Qt.black)
            self.sender().setPalette(new_palette)
            self.sender().setChecked(False)
        print(self.current_agent.partitions)

    def slotFinishButtonClicked(self):
        self.finish_adding_agents.close()
        self.close()

        self.add_agent_button.close()
        self.add_agent_button.close()
        self.add_agent_button.close()
        self.finish_adding_targets.deleteLater()
        self.add_target_button.deleteLater()
        self.view.setScene(None)
        self.view.close()
        self.show()
        for i in range(self.r * self.c):
            self.buttons[i].close()
        self.setFixedSize(700, 400)
        self.enter_safety = QLineEdit(self)
        self.enter_target_reachability = QComboBox(self)
        self.enter_sensor_uncertainty = QLineEdit(self)
        self.enter_liveness = QLineEdit(self)
        self.enter_safety.setPlaceholderText("Enter Belief Safety")
        self.enter_safety.setGeometry(QRect(25, 50, 300, 50))
        self.enter_safety.textChanged.connect(self.slotSafetyTextChanged)
        self.enter_liveness.setPlaceholderText("Enter Belief Liveness")
        self.enter_liveness.setGeometry(QRect(25, 100, 300, 50))
        self.enter_liveness.textChanged.connect(self.slotLivenessTextChanged)
        #self.enter_target_reachability.setPlaceholderText("Enter Target Reachability")

        #self.enter_target_reachability.textChanged.connect(self.slotReachabilityTextChanged)
        self.enter_sensor_uncertainty.setPlaceholderText("Enter Sensor Uncertainty")
        self.enter_sensor_uncertainty.setGeometry(QRect(25, 150, 300, 50))
        self.enter_sensor_uncertainty.textChanged.connect(self.slotSensorTextChanged)
        self.finish_adding_button = QPushButton(self)
        self.finish_adding_button.setText("Submit parameters and choose save location")
        self.finish_adding_button.setGeometry(QRect(25, 250, 700, 50))
        self.finish_adding_button.clicked.connect(self.slotSubmitButtonClicked)
        self.enter_target_reachability.addItem("Enter Target Reachability")
        self.enter_target_reachability.addItem("True")
        self.enter_target_reachability.addItem("False")
        self.enter_target_reachability.setGeometry(QRect(25, 200, 300, 50))
        self.enter_target_reachability.currentIndexChanged.connect(self.slotReachabilityTextChanged)
        self.enter_safety.show()
        self.enter_liveness.show()
        self.enter_target_reachability.show()
        self.enter_sensor_uncertainty.show()
        self.finish_adding_button.show()

    def slotSubmitButtonClicked(self):
        if self.target_reachability == "":
            message_box = QMessageBox()
            message_box.warning(self, "Error",
                                "Please select a value for Target Reachability")
        else:
            try:
                self.sensor_uncertainty = int(self.sensor_uncertainty)
                self.belief_safety = int(self.belief_safety)
                self.belief_liveness = int(self.belief_liveness)
            except ValueError:
                message_box = QMessageBox()
                message_box.warning(self, "Error",
                                    "Please input an integer for each field")
            else:
                self.target_reachability = True if self.target_reachability == "True" else False

                dialog = QFileDialog(self)
                dialog.setFileMode(QFileDialog.Directory)
                if dialog.exec():
                    save_folder = dialog.selectedFiles()
                scale = (self.r, self.c)
                file_list = [self.imagePath[0], scale, cv2.INTER_LINEAR_EXACT]
                file_list = [self.imagePath[0], scale, cv2.INTER_LINEAR_EXACT]
                image = cv2.imread(self.imagePath[0], cv2.IMREAD_GRAYSCALE)
                image = cv2.resize(image, dsize=scale, interpolation=file_list[2])
                h, w = image.shape[:2]

                targets = [i.target_states for i in self.agent_list]
                initial = [i.initial_state for i in self.agent_list]
                moveobstacles = [i.initial_state for i in self.target_list]
                print("moveobstacles ", moveobstacles)
                print("num agents: ", self.num_agents)
                print("target states:", targets)
                print("initial states agents: ", initial)
                gwg = Gridworld(file_list, nagents=self.num_agents, targets=targets,  initial=initial,
                                moveobstacles=moveobstacles)
                gwg.colorstates = [set(), set()]
                gwg.render()
                gwg.draw_state_labels()
                belief_ncols = gwg.ncols - self.sensor_uncertainty + 1
                belief_nrows = gwg.nrows - self.sensor_uncertainty + 1
                sensor_uncertain_dict = dict.fromkeys(range(belief_ncols * belief_nrows))
                agent_list = []
                for i in range(len(self.agent_list)):
                    new_map = {}
                    for j in range(len(self.agent_list[i].partitions)):
                        new_map[j] = self.agent_list[i].partitions[j]
                    agent_list.append(new_map)

                for i in range(belief_nrows):
                    for j in range(belief_ncols):
                        belief_gridstate = i * belief_ncols + j
                        sensor_uncertain_dict[belief_gridstate] = set()
                        for srow in range(i, i + self.sensor_uncertainty):
                            for scol in range(j, j + self.sensor_uncertainty):
                                gridstate = gwg.rcoords((srow, scol))
                                uset = list(itertools.product(['E', 'S', 'R'], repeat=self.sensor_uncertainty - 1))
                                for u in uset:
                                    snext = copy.deepcopy(i * gwg.ncols + j)
                                    for v in range(self.sensor_uncertainty - 1):
                                        act = u[v]
                                        snext = np.nonzero(gwg.prob[act][snext])[0][0]
                                    # if gridstate not in iset[belief_gridstate]:
                                    sensor_uncertain_dict[belief_gridstate].add(snext)
                                # sensor_uncertain_dict[belief_gridstate].add(gridstate)
                j = 0
                for n in self.agent_list:
                    for i in n.partitions:
                        n.allowed_states.extend(i)
                    obj = compute_all_vis.img2obj(image)
                    # compute visibility for each state
                    iset = compute_all_vis.compute_visibility_for_all(obj, h, w, radius=n.vis_dist)
                    write_structured_slugs.write_to_slugs_imperfect_sensor(save_folder[0], gwg, n.initial_state, moveobstacles[0], iset,
                                                                           n.target_states, n.velocity, n.vis_dist, n.allowed_states,
                                                                           [],
                                                                           agent_list[j], belief_safety=0, belief_liveness=1,
                                                                           target_reachability=False,
                                                                           sensor_uncertainty=self.sensor_uncertainty,
                                                                           sensor_uncertain_dict=sensor_uncertain_dict)
                    j += 1

                self.close()

    def slotSensorTextChanged(self, s):
        self.sensor_uncertainty = s

    def slotSafetyTextChanged(self, s):
        self.belief_safety = s

    def slotReachabilityTextChanged(self, s):
        if s == 0:
            self.target_reachability = ""
        elif s == 1:
            self.target_reachability = True
        elif s == 2:
            self.target_reachability = True

    def slotLivenessTextChanged(self, s):
        self.belief_liveness = s

    def mousePressEvent(self, event):
        if self.is_partition_selection:
            self.origin = event.pos()
            self.rubberband.setGeometry(
                QRect(self.origin, QSize()))
            self.rubberband.show()
        QWidget.mousePressEvent(self, event)

    def mouseMoveEvent(self, event):
        if self.is_partition_selection:
            if self.rubberband.isVisible():
                self.rubberband.setGeometry(
                    QRect(self.origin, event.pos()).normalized())
        QWidget.mouseMoveEvent(self, event)

    def mouseReleaseEvent(self, event):
        if self.is_partition_selection:
            if self.rubberband.isVisible():
                self.rubberband.hide()
                rect = self.rubberband.geometry()
                state_set = set()
                make_red = set()
                for child in self.findChildren(QLabel):
                    if rect.intersects(child.geometry()):
                        try:
                            state_set.add(int(child.text()))
                        except ValueError:
                            pass
                invalid_selection = False
                for state in state_set:
                    print("current partitions", self.current_agent.partitions)
                    for i in range(len(self.current_agent.partitions) - 1):
                        for j in range(len(self.current_agent.partitions[i])):
                            if self.current_agent.partitions[i][j] == state:
                                invalid_selection = True
                                for s in state_set:
                                    self.buttons[s].setStyleSheet("QLabel {background-color : transparent; }")
                                make_red.add(state)
                    if not invalid_selection:
                        if state not in self.current_agent.partitions[len(self.current_agent.partitions) - 1]:
                            print("adding state", state)
                            self.current_agent.partitions[len(self.current_agent.partitions) - 1].append(state)
                            self.buttons[state].setStyleSheet("QLabel {background-color : red; }")
                        else:
                            print("removing state", state)
                            self.current_agent.partitions[len(self.current_agent.partitions) - 1].remove(state)
                            self.buttons[state].setStyleSheet("QLabel {background-color : transparent; }")

                if invalid_selection:
                    for state in make_red:
                        self.buttons[state].setStyleSheet("QLabel {color : red; }")
                    message_box = QMessageBox()
                    message_box.warning(self, "Error",
                                        "One or more of these states is already in a partition")
                    return

        QWidget.mouseReleaseEvent(self, event)


class AddWindow(QWidget):

    initial_state = None
    velocity = None
    vis_dist = None
    allowed_states = []
    partitions = []

    def __init__(self, window_type, parent):
        super().__init__(parent)
        self.window_type = window_type
        self.setWindowFlags(Qt.Window)
        self.setFixedSize(500, 400)
        #self.enterInitialState = QLineEdit(self)
        self.enterVelocity = QLineEdit(self)
        self.enterVisibilityDist = QLineEdit(self)
        layout = QVBoxLayout(self)
        self.enterVelocity.setPlaceholderText("Enter " + self.window_type + "'s velocity")
        self.enterVisibilityDist.setPlaceholderText("Enter " + self.window_type + "'s visibility distance")

        #layout.addWidget(self.enterInitialState)
        layout.addWidget(self.enterVelocity)
        layout.addWidget(self.enterVisibilityDist)
        group = QGroupBox(self)
        group.setLayout(layout)
        group.setGeometry(0, 0, 500, 300)
        self.submit_button = QPushButton(self)
        self.submit_button.setText("Submit Parameters")
        self.submit_button.setGeometry(QRect(0, 300, 500, 50))
        self.submit_button.clicked.connect(self.slotSubmitButtonClicked)
        self.default_button = QPushButton("Use Default Parameters", self)
        self.default_button.setGeometry(QRect(0, 350, 500, 50))
        self.default_button.clicked.connect(self.defaultsUsed)
        self.default_button.show()
        group.show()

    def slotSubmitButtonClicked(self):
        try:
            #self.initial_state = int(self.enterInitialState.text())
            self.velocity = int(self.enterVelocity.text())
            self.vis_dist = int(self.enterVisibilityDist.text())
        except ValueError:
            message_box = QMessageBox()
            message_box.warning(self, "Error",
                                "Velocity or Visibility input is invalid")
            return

        if self.window_type == "target":
            self.parent().addTarget(Target(self.initial_state, self.velocity, self.vis_dist))
            self.close()
        elif self.window_type == "agent":
            try:
                #allowed_states = [int(i) for i in self.enterAllowedStates.text().split()]
                #target_states = [int(i) for i in self.enterTargetStates.text().split()]
                #print(allowed_states)
                print("addWindowsubmit")
                self.parent().addAgent(
                    Agent(self.velocity, self.vis_dist))
                self.close()
            except ValueError:
                message_box = QMessageBox()
                message_box.warning(self, "Error",
                                    "Please enter Allowed States and Target states as numbers separated by spaces")

    def defaultsUsed(self):
        self.vis_dist = max(self.parent().c, self.parent().r) * 10
        if self.window_type == "agent":
            self.velocity = 3
            self.parent().addAgent(Agent(self.velocity, self.vis_dist))
        else:
            self.velocity = 1
            self.parent().addTarget(Target(self.initial_state, self.velocity, self.vis_dist))
        self.close()


class Target:

    def __init__(self, initial_state, velocity, vis_dist):
        self.initial_state = initial_state
        self.velocity = velocity
        self.vis_dist = vis_dist


class Agent:

    def __init__(self, velocity, vis_dist):
        #self.initial_state = initial_state
        self.velocity = velocity
        self.vis_dist = vis_dist
        self.allowed_states = []
        self.partitions = []
        self.initial_state = -1
        self.target_states = []


if __name__ == "__main__":
    a = QApplication(sys.argv)
    myApp = MainWindow()
    myApp.show()
    sys.exit(a.exec_())
