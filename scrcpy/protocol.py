"""scrcpy 控制协议常量"""

# 控制消息类型
TYPE_KEY = 0
TYPE_TOUCH = 2
TYPE_SCROLL = 3
TYPE_COMMAND = 4

# 触摸动作
ACTION_DOWN = 0
ACTION_UP = 1
ACTION_MOVE = 2

# 按键动作
KEY_ACTION_DOWN = 0
KEY_ACTION_UP = 1

# 常用 Android 键码
KEYCODE_BACK = 4
KEYCODE_HOME = 3
KEYCODE_MENU = 187
KEYCODE_VOLUME_UP = 24
KEYCODE_VOLUME_DOWN = 25
KEYCODE_POWER = 26

# scrcpy 消息结构
META_KEY_LEN = 8  # pointer_id 占 8 字节
TOUCH_HEADER_SIZE = 1 + 1 + META_KEY_LEN  # type + action + pointer_id
