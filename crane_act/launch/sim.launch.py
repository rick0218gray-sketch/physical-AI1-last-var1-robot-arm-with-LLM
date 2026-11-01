# CRANE+ V2 + table in Ignition Gazebo, without MoveIt (lighter on RAM).
# Based on crane_plus_gazebo/no_moveit_crane_plus_with_table.launch.py (Apache-2.0, RT Corporation)
# Added: gui:=false runs the Gazebo server only (headless data collection).
import os

from ament_index_python.packages import get_package_share_directory
from crane_plus_description.robot_description_loader import RobotDescriptionLoader
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node, SetParameter


def _gazebo(context):
    gui = LaunchConfiguration('gui').perform(context).lower() in ('1', 'true', 'yes')
    env = {'IGN_GAZEBO_SYSTEM_PLUGIN_PATH': os.environ['LD_LIBRARY_PATH'],
           'IGN_GAZEBO_RESOURCE_PATH': os.path.dirname(
               get_package_share_directory('crane_plus_description'))}
    world_file = os.path.join(
        get_package_share_directory('crane_plus_gazebo'), 'worlds', 'table.sdf')
    gui_config = os.path.join(
        get_package_share_directory('crane_plus_gazebo'), 'gui', 'gui.config')
    if gui:
        cmd = ['ign gazebo -r', world_file, '--gui-config', gui_config]
    else:
        cmd = ['ign gazebo -r -s', world_file]
    return [ExecuteProcess(cmd=cmd, output='screen', additional_env=env, shell=True)]


def generate_launch_description():
    description_loader = RobotDescriptionLoader()
    description_loader.use_gazebo = 'true'
    description_loader.use_ignition = 'true'
    description_loader.gz_control_config_package = 'crane_plus_control'
    description_loader.gz_control_config_file_path = 'config/crane_plus_controllers.yaml'
    description = description_loader.load()

    def spawner(name):
        return ExecuteProcess(cmd=[f'ros2 run controller_manager spawner {name}'],
                              shell=True, output='screen')

    return LaunchDescription([
        DeclareLaunchArgument('gui', default_value='true'),
        SetParameter(name='use_sim_time', value=True),
        OpaqueFunction(function=_gazebo),
        Node(package='ros_gz_sim', executable='create', output='screen',
             arguments=['-topic', '/robot_description', '-name', 'crane_plus',
                        '-z', '1.015', '-allow_renaming', 'true']),
        Node(package='robot_state_publisher', executable='robot_state_publisher',
             name='robot_state_publisher', output='both',
             parameters=[{'robot_description': description}]),
        spawner('joint_state_broadcaster'),
        spawner('crane_plus_arm_controller'),
        spawner('crane_plus_gripper_controller'),
        Node(package='ros_gz_bridge', executable='parameter_bridge',
             arguments=['/clock@rosgraph_msgs/msg/Clock[ignition.msgs.Clock'],
             output='screen'),
    ])
