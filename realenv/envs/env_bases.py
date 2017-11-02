## Issue related to time resolution/smoothness
#  http://bulletphysics.org/mediawiki-1.5.8/index.php/Stepping_The_World

from realenv.core.physics.scene_building import SinglePlayerBuildingScene
from realenv.core.physics.scene_stadium import SinglePlayerStadiumScene
import pybullet as p
import time
import random
import zmq
import math
import argparse
import os
import json
import numpy as np
from transforms3d import euler, quaternions
from realenv.core.physics.physics_object import PhysicsObject
from realenv.core.render.profiler import Profiler
from realenv.configs import *
import gym, gym.spaces, gym.utils, gym.utils.seeding
import sys


class BaseEnv(gym.Env):
    """
    Base class for loading MJCF (MuJoCo .xml) environments in a Scene.
    These environments create single-player scenes and behave like normal Gym environments.
    Multiplayer is not yet supported
    """

    metadata = {
        'render.modes': ['human', 'rgb_array'],
        'video.frames_per_second': 60
        }

    def __init__(self):
        ## Properties already instantiated from SensorEnv/CameraEnv
        #   @self.human
        #   @self.robot
        if (self.physicsClientId<0):
            self.physicsClientId = p.connect(p.SHARED_MEMORY)
            if (self.physicsClientId < 0):
                if (self.human):
                    self.physicsClientId = p.connect(p.GUI)
                    if MAKE_VIDEO:
                        #self.set_window(-1, -1, 1024, 512)
                        self.set_window(-1, -1, 512, 512)
                else:
                    self.physicsClientId = p.connect(p.DIRECT)

        self.scene = self.create_single_player_scene(SCENE_TYPE)
        self.robot.scene = self.scene

        self.camera = Camera()
        self._seed()
        self._cam_dist = 3
        self._cam_yaw = 0
        self._cam_pitch = -30
        self._render_width =320
        self._render_height = 240

        self.action_space = self.robot.action_space
        self.observation_space = self.robot.observation_space

    def configure(self, args):
        self.robot.args = args
    def _seed(self, seed=None):
        self.np_random, seed = gym.utils.seeding.np_random(seed)
        self.robot.np_random = self.np_random # use the same np_randomizer for robot as for env
        return [seed]

    def _reset(self):
        p.configureDebugVisualizer(p.COV_ENABLE_GUI,0)
        p.configureDebugVisualizer(p.COV_ENABLE_KEYBOARD_SHORTCUTS, 0)
        p.configureDebugVisualizer(p.COV_ENABLE_MOUSE_PICKING, 1)
        #p.configureDebugVisualizer(p.COV_ENABLE_SHADOWS, 0)
        #p.configureDebugVisualizer(p.COV_ENABLE_TINY_RENDERER, 1)
        #p.configureDebugVisualizer(p.COV_ENABLE_RENDERING, 0)
    
        #visualid = p.createVisualShape(p.GEOM_MESH, fileName=os.path.join(pybullet_data.getDataPath(), 'cube.obj'),
        #                               meshScale=[0.3, 0.3, 0.3], rgbaColor=[1, 0, 0, 0.7])
        #physicsid = p.createMultiBody(baseVisualShapeIndex=visualid, baseCollisionShapeIndex=-1, basePosition=[0, 0, 2])
        #keep code here for reference


        self.frame = 0
        self.done = 0
        self.reward = 0
        dump = 0
        s = self.robot.reset()
        self.scene.episode_restart()
        self.potential = self.robot.calc_potential()
        return s

    def _render(self, mode, close):
        if (mode=="human"):
            self.human = True
        if mode != "rgb_array":
            return np.array([])
        
        base_pos=[0,0,0]
        if (hasattr(self,'robot')):
            if (hasattr(self.robot,'body_xyz')):
                base_pos = self.robot.body_xyz
        
        view_matrix = p.computeViewMatrixFromYawPitchRoll(
            cameraTargetPosition=base_pos,
            distance=self._cam_dist,
            yaw=self._cam_yaw,
            pitch=self._cam_pitch,
            roll=0,
            upAxisIndex=2)
        proj_matrix = p.computeProjectionMatrixFOV(
            fov=60, aspect=float(self._render_width)/self._render_height,
            nearVal=0.1, farVal=100.0)
        (_, _, px, _, _) = p.getCameraImage(
        width=self._render_width, height=self._render_height, viewMatrix=view_matrix,
            projectionMatrix=proj_matrix,
            renderer=p.ER_BULLET_HARDWARE_OPENGL
            )
        rgb_array = np.array(px)
        rgb_array = rgb_array[:, :, :3]
        return rgb_array

    def get_action_dim(self):
        return len(self.robot.ordered_joints)

    def get_observation_dim(self):
        return 1

    def _close(self):
        if (self.physicsClientId>=0):
            p.disconnect(self.physicsClientId)
            self.physicsClientId = -1
    
    def set_window(self, posX, posY, sizeX, sizeY):
        values = {      
            'name': "Robot",  
            'gravity': 0,
            'posX': int(posX),
            'posY': int(posY),
            'sizeX': int(sizeX),
            'sizeY': int(sizeY)
        }
        cmd = 'wmctrl -r \"Bullet Physics\" -e {gravity},{posX},{posY},{sizeX},{sizeY}'.format(**values)
        os.system(cmd)

        cmd = "xdotool search --name \"Bullet Physics\" set_window --name \"Robot's world\""
        os.system(cmd)

    def create_single_player_scene(self, scene ='building'):
        if scene == 'building':
            self.building_scene = SinglePlayerBuildingScene(self.robot, gravity=9.8, timestep=self.timestep, frame_skip=self.frame_skip)
        elif scene == 'stadium':
            self.building_scene = SinglePlayerStadiumScene(self.robot, gravity=9.8, timestep=self.timestep, frame_skip=self.frame_skip)
        else:
            self.building_scene = None
            print("Scene not created")
        return self.building_scene
        

    def HUD(self, state, a, done):
        pass



class Camera:
    def __init__(self):
        pass

    def move_and_look_at(self,i,j,k,x,y,z):
        lookat = [x,y,z]
        distance = 10
        yaw = 10
        p.resetDebugVisualizerCamera(distance, yaw, -20, lookat)


