JoyInside平台接入指引
JoyInside平台简介JoyInside是京东推出的附身智能品牌，致力于为硬件注入灵魂，使其升级为能够理解人类、具备情感、会聊天能执行懂陪伴的智能伙伴。
JoyInside平台，提供完整的语音智能体搭建、API接入方案，方便品牌方/开发者基于平台能力快速完成产品定义、硬件设备接入，让硬件开口说话，用自然语言交互驱动设备动作。
平台提供的核心能力说明：
智能体搭建
在JoyInside平台，可自主创建产品应用，选用系统内置技能，调整人设、音色及对话策略，快速完成语音对话智能体搭建。
第三方技能扩展
支持开发者自建第三方技能，通过API方式注册到平台，增加新技能并接入到智能体中使用。此外，也支持自定义指令，配合端侧操控设备。
在线调试
支持在线调试、发布智能体，便于实时调优。
API接入指引
具备鉴权、设备注册、websocket语音对话流接入的全链路API，参照文档即可完成硬件接入。
快速入门步骤一 企业注册操作步骤
示例
step1:登录注册
点击网页https://joy-inside.jd.com
进入个人用户登录页面
选择京东APP/微信扫码登录个人京东账号
注意：此处暂未支持企业账号，需使用个人账号登录
step2：提交企业信息，等待审核
注意：参与创新大赛的人员/团队，请按“AI创新大赛-赛道名称-项目名称”格式填写企业名称，否则可能导致账号审核时无法识别并快速审核通过。
例如：AI创新大赛-探索者赛道-JoyInside项目
其余企业/品牌申请，按照实际企业主体名称填写即可。
step3：审核通过，进入工作区首页
步骤二 创建产品型号        型号是指一类硬件设备的标识符，用于区分不同类型的设备，与硬件产品强关联。产品型号可以在资源管理>型号库 中进行创建和维护。
注意型号值是唯一的，不可以重复
操作步骤
示例
step1：资源管理>型号库>新建型号
自定义产品型号名称
步骤三 创建应用&搭建智能体        应用是用于实现特定交互功能的模块化单元，一个应用对应一个硬件产品型号，用于定义其交互功能，是产品最核心的配置模块，也即其大脑。应用内可以包含多个技能、指令、人设、音色等配置，支持自定义和交互调试。
1.新建应用操作步骤
示例
step1：应用管理>新建应用
step2：填写应用配置项
应用名称：自定义
产品型号：选择【步骤二】中创建好的产品型号
接入类型：
语音智能体接入：输入输出为语音内容（推荐）
文本智能体接入：输入输出为文本内容
默认音色：即智能体在语音对话交互时使用的默认音色
技能：技能是指应用中实现特定功能的模块，可以是系统内置技能或企业自定义技能。可以在此处预选，也可以创建应用后在应用配置详情中编辑。详见【3.技能选择与编辑】
指令：指令用于触发特定的操作，帮助系统理解用户的要求并执行相应的动作。可以在此处预选，也可以创建应用后在应用配置详情中编辑。详见【4.指令选择与编辑】
开场白：开场白主要用于首次建立连接时，主动下发的问候语。详见【5.交互策略配置】
静默消息推送：可以在特定条件下向用户推送信息。 详见【5.交互策略配置】
2.人设与音色配置操作步骤
示例
step1:进入应用配置
在应用管理中，直接点击目标应用卡片，或配置详情。
应用卡片下方即为应用ID
step2:切换音色
音色分为系统音色和自定义音色。
自定义音色详见「步骤四 音色配置」
点击音色可切换音色，切换后应用的默认音色为切换后的新音色；

step2:全局人设编辑
全局人设编辑窗口可通过提示词自定义人物设定，点击编辑框右上角可以在人设中插入系统变量。
系统变量支持：
${systemTime}：系统时间
${location}：设备地点
${memoBaseContent}：长期记忆


3.技能选择与编辑       平台通过“技能”模块赋予智能体特定的能力。平台支持选用开箱即用的「系统技能」，也支持企业根据业务需求灵活接入「自定义技能」。
系统技能选择与编辑
       系统技能是预置的标准能力（如闲聊、天气查询等），企业可直接勾选使用，并支持对部分技能进行微调。
操作步骤
示例
Step 1：进入应用技能配置
在应用管理中，直接点击目标应用卡片，或配置详情，进入技能配置模块。  
Step 2：添加技能
技能列表中展示的技能为在「应用创建」时勾选的技能
添加技能：点击【添加技能】，选择目标技能即可加入技能列表中。
Step 3：系统技能个性化编辑（以“闲聊”技能为例）
点击系统技能卡片右侧的“编辑”按钮，可对以下字段进行微调：
提示词模式
系统内置：使用平台默认优化的 Prompt，用户不可见。
自定义提示词：提供基础模板参考，支持在此基础上自定义Prompt，管理员可自行定义特定的回复内容。
插入系统变量：
在提示词编辑框中，点击右上角的「提示」按钮，弹出“系统变量”选择列表。
变量选择：勾选需要的变量，点击“保存”，系统会自动将变量以 ${variableName}的格式插入到光标所在位置。
常用变量说明：
${systemTime}：系统时间
${location}：设备地点
${memoBaseContent}：长期记忆
自动拼接全局人设
勾选后，系统会自动将应用的【全局人设】信息拼接到该技能的 Prompt 头部，确保智能体在闲聊时保持人设一致性。
关联知识库
支持为闲聊技能挂载企业知识库。配置后，当问题召回知识库内容时，优先基于知识库内容回复。
自定义技能创建与使用
        自定义技能允许企业自定义扩展第三方技能，在平台配置技能准入条件+ API服务关联，即可扩展智能体的业务能力。
说明：调用技能时，系统会默认携带部分会话信息给下游API，企业可酌情使用。
操作步骤
示例
Step 1：新建自定义技能
进入 资源管理 > 技能库配置
点击右上角「新建技能」按钮，进行配置。
Step 2：填写核心信息
技能名称：输入易于辨识的名称，建议包含动词，在企业内需唯一。
Step 3：配置触发规则
技能准入描述：技能准入描述：用于识别技能准入的核心信息。即告诉 AI 在什么情况下应该触发这个技能。内容建议包含：意图定义、标准触发条件、不可触发条件。明确的规则能有效降低技能的误识别率。
爆款推荐：当用户明确希望获取当前热门商品、促销活动、购物榜单或要求智能体进行购物推荐时触发。

标准触发条件：
用户明确表达求推荐、看爆款、看榜单的意图。
示例：今天有什么爆款、给我推荐点好东西、京东现在热销榜第一是什么、今天有什么打折的吗

不可触发条件：
命中以下情况不应归类为爆款推荐
用户询问某一个具体商品的情况（因本技能不支持提取商品名称参数，故不拦截此类问题）。
-- 示例：帮我查一下苹果15多少钱、那双耐克鞋还有货吗
用户只是泛泛表达消费情绪，未明确要求推荐。
-- 示例：我今天发工资了想花钱、最近买东西太多要剁手了
示例：通过提供对话范例，可辅助提升模型对特定技能的识别准确率。
输入正反例来“教”模型识别；
格式参考：
正例：
  1.请给我推荐点爆款商品吧
  2.给我推荐点好东西
反例：
  1.今天天气怎么样？
  2.北京今天的天气？
Step 4：关联服务
技能触发后具体调用的后端 API 接口。
在“调用 API”下拉框中，选择已在开发者中心注册并启用的 API 服务；
若下拉列表为空，请先前往“开发者中心”完成 API 注册并启用。详见【其他-外部API注册】
Step 5：保存
点击“保存”后即可使用该技能。
发布成功后，该自定义技能将出现在【应用管理 > 添加技能】的可选列表中，勾选即可为您的智能体配置此项新技能。
4.指令选择与编辑        指令即用户与智能体交互时具体的操作命令，可以触发特定的行为或技能。当命中指令时，会下发指令事件，同时会根据用户问题，下发一句回复的话术（话术会结合输入动态生成）。
操作步骤
示例
step1:添加指令
点击添加，允许选择系统指令或自定义指令
系统指令包括：音量控制、电量查询
step2：创建自定义指令集
进入资源管理>指令库，点击新建
填写指令集名称
适用场景：默认为通用
产品品类：默认为通用
描述：30字以内的指令集描述说明
step3：创建自定义指令
指令集创建成功后，点击【查看】进入指令集，即可新增指令
填写指令名称
填写指令编码，指令编码为全英文，可包含"-""_"字符
指令描述：不参与意图识别，只用于展示
识别提示词：识别提示词用于定义指令的触发条件，即当用户输入与提示词相匹配的内容时，系统可以据此识别出用户想要执行的指令。
例句：作为指令识别的参考，帮助系统更准确的匹配用户输入和指令意图
槽位：槽位是指用户输入的指令中，需要提取的关键参数。例如在调高音量的指令中，【音量值】就是槽位。
字段名：槽位的标识符，全英文，可包含"-""_"字符
槽值：与槽位对应的值，例如具体的音量数值
槽值提取提示词：用于引导系统从用户输入中提取槽值的关键词或规则
槽位为非必填项，根据指令性质按需填写。
自定义指令创建完成后，即可以在新建或编辑应用时选择该指令

5.交互策略配置操作步骤
示例
开场白主要用于首次建立连接时，主动下发的问候语，支持轮播话术，最多支持五条轮播。
例如：你好！今天有什么有趣的事情吗？
创建/编辑应用时，【是否开启开场白】选择“开”，才能编辑开场白

当对话过程中用户保持沉默一段时间后，设备会自动向用户推送唤醒信息，以重新激活交互。
静默推送的提示词是系统内置，暂不支持自定义，但允许在静默推送提示词中拼接全局人设信息，使推送内容符合人设。
支持在创建应用/编辑应用时添加时段控制和时间间隔控制，最多支持添加五组控制规则。
推送时间段：例如将时间段设置为7：00-20：00，则只有这个时间段内会开启静默推送。
静默推送时间阈值，即对话过程中用户保持沉默的时间超过该时间阈值时，会启动静默推送。
创建/编辑应用时，【是否开启静默推送】选择“开”，才能编辑静默推送
步骤四 注册设备        设备注册是为智能硬件平台上创建唯一身份标识的过程，类似于给设备办理身份证。注册后硬件设备即可获得合法接入平台服务的资格，平台可以识别、管理并授权设备使用相关功能，实现安全可靠的连接和服务交互。
        设备注册支持两种方式：测试阶段可在设备管理处手动添加单个虚拟设备；正式接入阶段则通过API批量添加正式设备。如需使用API批量注册，请参考步骤六的端侧接入指南。
操作步骤
示例
step1：新建设备
进入设备管理，点击新建
step2：填写设备相关配置项
类型
实体设备
虚拟设备
测试阶段只能选择虚拟设备
所属应用：选择所属应用后，该设备可以使用所属应用的相关功能
名称：自定义
SN编码：SN编码（产品序列号）是制造商为每个产品分配的唯一标识符，用于区分和追踪单个设备或产品。
音色：选择语音交互时的音色
描述：简单描述设备信息
步骤五 智能体调试        调试窗用于测试和调试智能体交互的工具，支持模拟用户输入、查看对话过程与结果，并提供完整的调试信息展示。
操作步骤
示例
step1：调试设置
在调试窗口，系统自动完成初始化链接，无需额外配置即可测试
允许自定义位置、语言等测试参数
step2：开始调试
保存草稿后才可以调试
点击开始调试，即可通过输入框输入测试消息
信息面板会展示意图识别、智能体执行等中间状态
step3：会话管理
会话ID(sessionID)在每次打开测试窗口时自动生成
关闭或刷新页面后重新打开将创建新会话
对话历史支持60轮，超出部分自动清理

步骤六 端侧接入参考《端侧接入-开发指引》。

其他1.外部API注册该功能模块目前仅用于第三方技能扩展。当企业需要创建“自定义技能”时，必须先在此处完成 API 的注册与授权配置，随后才能在技能库中进行关联绑定。
操作步骤
示例
核心规则说明
在进行 API 注册前，请务必了解以下平台规则（如右图蓝框所示）：
鉴权限制：目前平台仅支持 Service Token (个人令牌) 这一种鉴权方式。
安全保护：如果某个 API 已被技能库中的技能关联，则不允许直接删除。
操作步骤示例
Step 1：进入 API 管理与新建
在左侧菜单栏点击 开发者中心 > 第三方服务，进入 API 管理列表。点击页面右上角的「+ 新建API」按钮，展开配置抽屉。
Step 2：填写基础信息
API 名称：为接入的服务起一个易于辨识的名字
注意：只能包含字母、数字和下划线，不支持中文、空格及特殊符号，最多20个字符。
私网连接：如服务暴露在公网，请保持默认的“不使用私网连接”。
技能 URL：输入后端服务的完整接口地址。
Step 3：配置请求参数 (Header)
部分接口可能需要在请求头中传递特定参数
点击「+」号可新增 Header 字段。
在Key中填写参数名（如User-Agent），在Value中填写对应的值。不需要则留空。
Step 4：配置鉴权信息
为保障接口安全，平台调用服务时需要进行身份验证。
授权方式：固定选择Service Token。
参数位置：根据接口的要求，选择该 Token 是放在Header（请求头）还是Query（URL参数）中传给服务器。
Token 值：输入系统生成的鉴权密钥。
Step 5：保存校验与启用
点击右下角的「保存并校验」，系统会尝试验证配置格式。
关键最后一步：保存成功后返回列表页，找到刚创建的 API，将状态开关拨到“启”。此时，该 API 就可以在创建“自定义技能”时被选用
2.自定义变量使用对话链路中，支持端侧在请求时自定义传入扩展信息，并在提示词中，按照固定格式取用对应信息，请求方法参数下文【上行事件--主动更新对话上下文】。注意：使用此功能，需向JoyInside运营团队申请权限。
传入示例{
    "code": 200,
    "requestId": "1",
    "mid": "1",
    "contentType": "ACTIVITY",
    "content": {
        "activityType": "CLIENT_UPDATE_CHAT_CONTEXT",
        "effectiveTimeMinutes": 5, // 记忆XX分钟，取值范围：[1~1440] 
        "kvData": {
            // 自定义拓展信息
            "自定义字段名": "自定义值"
        }
    }
}


// 服务端收到CLIENT_UPDATE_CHAT_CONTEXT事件后，会下发CLIENT_CHAT_CONTEXT_RECEIVED下行事件
{
    "code": 200,
    "msg": "Activity success",
    "requestId": "1",
    "contentType": "EVENT",
    "content": {
        "roundId": "1_3",
        "activityType": "CLIENT_CHAT_CONTEXT_RECEIVED",
        "activityData": {}
    },*
    "t": 1775802187178
}
提示词取用方式在提示词内需要插入的位置，按照此格式撰写，即可渲染：${(extInfo.[字段名])!""}，若存在多层级，则输入：${(extInfo.app1.key1)!""}。示例：${(extInfo.chessAnalysis.opponent)!""}
3.音色复刻通过“音色库”，端侧可以在平台内上传一段语音，快速复刻成“专属音色”，并在应用或设备中直接使用，打造更符合品牌气质的声音形象。
操作步骤
示例
Step 1：进入音色库并新建
打开 资源管理 > 音色库，点击“新建”，进入音色复刻页面
Step 2：上传语音
从本地上传语音文件（单段音频）
时长要求：严格限制时长在 3–15 秒（需要整段连续音频，不能有较长停顿静音）
上传后可“下载原音频”或“删除重传”
Step 3：填写信息与授权
音色名称：上传后默认以“文件名”填充，可修改
命名规则：
自定义音色名称在“同一企业内”需唯一
可与系统音色同名，最终以“音色类型”区分
隐私授权：勾选“我已获得录音素材的合法授权”（未勾选无法提交）
Step 4：复刻并保存
点击“确定”发起复刻，完成后该音色将出现在音色库列表
试听：支持在列表中“试听”，确认合成效果
编辑：对自定义音色进行编辑；音色系统内置音色不可编辑、不可删除
删除：删除前请确认该音色未被应用或设备使用，若音色被占用将无法被删除
Step 5：在应用与设备中使用
应用管理 > 配置详情：在“音色”选择框中，系统与自定义音色统一展示，可直接切换
设备管理 > 新建设备/编辑设备：同样支持选择已复刻的自定义音色
温馨提示：建议先在在线调试中体验对话效果，再决定是否发布

端侧接入-开发指引1.获取相关参数操作步骤
示例
step1:获取AccessKey和SecretKey
进入开发者中心>API密钥，即可查看AccessKey和SecretKey
step2:获取vendorId（企业唯一标识）
进入个人信息>企业信息，获取企业ID（vendorId）
step3:获取AppID（应用唯一标识）
进入应用管理，获取目标应用ID（appId）
2.获取授权step1:获取有效签名签名用于验证请求的合法性，确保请求参数未被篡改。服务端会使用相同规则生成签名，若签名一致则视为合法请求。
参数说明
accessVersion（认证算法版本，目前只支持V2）
accessTimestamp（当前毫秒级时间戳，单位ms）
accessNonce（随机字符串，建议用UUID）
accessKeyId（开发者中心>API密钥中的AccessKey）
python示例代码
# -*- coding: utf-8 -*-
import binascii
import hashlib
import hmac


def generate_sign():
    # 准备参数
    params = {
        "accessVersion": "V2",
        "accessTimestamp": str(int(round(time.time() * 1000))),
        "accessNonce": str(uuid.uuid4()),
        "accessKeyId": "使用您的AccessKey"
    }

    # 统一参数格式，将params的key转为小写并排序（按参数名称的字母顺序排序）
    lower_key_params = {k.lower(): params[k] for k in params}
    sorted_params = sorted(lower_key_params.items(), key=lambda item: item[0])

    # 拼接key=value
    joint_params = '&'.join([f'{k}={str(v)}' for k, v in sorted_params])

    # 使用HMAC-MD5算法加密，计算签名
    h = hmac.new("使用您的SecretKey".encode('utf-8'), joint_params.encode('utf-8'), digestmod=hashlib.md5)
    return binascii.hexlify(h.digest()).decode('utf-8')
注意事项⚠️密钥安全：accessKeySecret必须保密，不要泄露或写在客户端代码中
⚠️时间戳有效期：确保与服务端时间误差在15分钟内
⚠️随机数防重放：accessNonce建议使用一次性随机值，防止请求被重复使用
✅编码一致：所有参数必须使用UTF-8编码
step2:获取访问令牌        Token是调用API时的身份凭证，类似于临时通行证。在后续所有API请求中都需要携带此Token进行身份验证。
接口信息
URL
https://api.joyinside.com/auth/getToken
请求方式
POST
接口作用
获取访问令牌
请求参数说明
字段名称
类型
是否必选
说明
accessKeyId
String
是
用户访问密钥ID，获取方式详见【1.获取相关参数】
accessTimestamp
String
是
13位当前Unix时间戳，值为请求前15分钟内的时间戳
accessNonce
String
是
签名唯一随机数，用于防止网络重放攻击，建议每次请求使用不同随机数
accessVersion
String
是
认证算法版本，当前固定值为V2
accessSign
String
是
签名。计算方式参考step1:获取有效签名
botId
String
否
设备唯一标识，若此前已经注册过设备，设备管理页面，设备【ID】列的内容即为botId。
botId与vendorId二者必选其一
vendorId
String
否
厂商唯一标识，获取方式详见【1.获取相关参数】
botId与vendorId二者必选其一
注意事项参数botId与vendorId同时存在时，优先使用botId生成授权令牌
新设备注册时，使用vendorId获取访问令牌
时间戳：确保与服务端时间误差在15分钟内
随机数：防止重复请求攻击，每次必须不同
如果使用botId获取令牌，获取 token 时，必须使用已经注册的 botid ，保证与其他 botid 不重复。
响应参数
字段名称
类型
是否必选
说明
accessToken
String
是
用户访问令牌
expireIn
Integer
是
访问令牌过期时间（秒）,有效期2小时，失效后重新生成或使用refreshToken生成新accessToken
refreshToken
String
是
刷新令牌，有效期为7天，有效期内可以刷新accessToken，失效后需重新获取
refreshExpireIn
Integer
是
刷新令牌过期时间（秒）
code
Integer
是
状态码
msg
String
是
状态对应信息
代码示例
import json
import time
import uuid
import requests

def get_token():
    params = {
        "accessKeyId": "使用您的AccessKey",
        "accessTimestamp": str(int(round(time.time() * 1000))),
        "accessNonce": str(uuid.uuid4()),
        "accessVersion": "V2"
    }

    params['accessSign'] = generate_sign(ACCESS_VERSION, params["accessTimestamp"], params["accessNonce"],ACCESS_KEY, ACCESS_KEY_SECRET)

    # 厂商ID和设备ID 二选一/都传
    # params["botId"] = "注册返回的设备Id"
    params["vendorId"] = "您的企业Id"

    res = requests.post("https://api.joyinside.com/auth/getToken", json=params)
    if res.status_code != 200:
        logger.error("请求异常: %s", res.status_code)
        return None

    logger.info("获取授权结果: %s", res.text)
    res_json = json.loads(res.text)
    return res_json["accessToken"]

def generate_sign(accessVersion, accessTimestamp, accessNonce, accessKeyId, accessKeySecret):
    params = {
        "accessVersion": "V2",
        "accessTimestamp": str(int(round(time.time() * 1000))),
        "accessNonce": str(uuid.uuid4()),
        "accessKeyId": "使用您的AccessKey"
    }

    # 将params的key转为小写并排序
    lower_key_params = {k.lower(): params[k] for k in params}
    sorted_params = sorted(lower_key_params.items(), key=lambda item: item[0])

    # 拼接key=value
    joint_params = '&'.join([f'{k}={str(v)}' for k, v in sorted_params])

    # 计算签名
    h = hmac.new("使用您的SecretKey".encode('utf-8'), joint_params.encode('utf-8'), digestmod=hashlib.md5)
    return binascii.hexlify(h.digest()).decode('utf-8')
step3:设备注册       设备注册是为智能硬件平台上创建唯一身份标识的过程，类似于给设备办理身份证。注册后硬件设备即可获得合法接入平台服务的资格，平台可以识别、管理并授权设备使用相关功能，实现安全可靠的连接和服务交互。
        设备注册支持两种方式：一是在设备管理处手动添加单个设备，二是通过API批量添加设备。如果已在设备管理处添加过设备，且无需批量注册设备，这一步可以跳过。
接口信息
URL
https://api.joyinside.com/device/register
请求方式
POST
接口作用
设备注册
请求参数
Header
字段名称
类型
必选
说明
Authorization
string
是
Bearer ${accessToken} 获取方式参考【step2获取访问令牌】
body
字段名称
类型
必选
说明
vendorId
string
是
厂商唯一标识。获取方式详见【1.获取相关参数】
appId
string
是
应用唯一标识。获取方式详见【1.获取相关参数】
type
string
是
设备类型。取值：
PHYSICAL_ROBOT，生产设备
APP_ROBOT，测试设备
name
string
是
设备名称
deviceId
string
是
设备唯一标识，厂商需要保证设备ID唯一，建议使用设备的SN编码作为deviceId，SN编码（产品序列号）是制造商为每个产品分配的唯一标识符，用于区分和追踪单个设备或产品。
deviceModel
string
否
设备型号
timbreId
string
否
音色 id 
desc
string
否
描述信息
响应参数
字段名称
类型
必选
说明
state
string
是
返回状态。取值：
SUCCESS 成功; FAILURE 失败
code
string
是
返回码
result
string
是
描述信息
data
string
是
对话机器人ID , 用于后续对话 botId
代码示例
请求示例
import json
import time
import uuid
import requests

def register_bot():
    headers = {"Authorization": "Bearer " + "填入您的有效Token"}
    params = {
        "vendorId": "填入您的企业ID",
        "appId": "填入您的APP_ID",
        "deviceId": "建议使用设备SN编码",
        "type": "APP_ROBOT", # 代表测试设备
#        "type":"PHYSICAL_ROBOT", # 代表生产设备
        "name": "测试"
    }

    res = requests.post("https://ws.joyinside.com/device/register", headers=headers, json=params)
    if res.status_code != 200:
        print("请求异常", res.status_code)
        return None

    res_json = json.loads(res.text)
    return res_json["data"]
成功响应示例
{
  "state": "SUCCESS",
  "code": "0000",
  "result": "创建成功",
  "data": "0428f41d89fc436b8d63a529cf7141a7"
}
3.语音对话（1）基于websocket实现语音对话      JoyInside推出了流式语音对话 WebSocket 方案，用于实现用户与智能体之间的实时语音通话。该方案通过 WebSocket 协议提供高效、灵活的语音交互能力，适用于多种应用场景。
@startuml AI玩具交互时序图
actor "儿童（用户）" as Child
participant "AI玩具（终端设备）" as Toy
participant "JoyInside服务器" as Server
participant ASR
participant "内容审核" as Audit
participant "AI智能体" as AI
participant TTS
actor "设备管理（家长）" as Parent

== 前置授权与准备 ==
Parent -> Server : 设备配网 + 设备激活 + 隐私授权
Server --> Parent : 配网成功，设备合法注册

== 核心交互流程 ==
Child -> Toy : 启动设备
Toy -> Server : TLS 1.3加密传输：设备标识 + 访问令牌
Server -> Server : 设备合法性校验 / 令牌校验
alt 校验通过
    Server --> Toy : 检验成功，建立WebSocket连接
    Child -> Toy : 发起语音/按键指令
    Toy -> Toy : 本地预处理（唤醒词验证、降噪、事件指令）
    Toy -> Server : WebSocket传输：用户语音 + 上行事件指令
    group JoyInside服务内部交互
        Server -> ASR : 用户语音
        ASR -> ASR : VAD + 语音识别
        ASR --> Server : 语音识别结果
        par 语音识别结果内容审核
            Server -> Audit : 语音内容审核
            Audit --> Server : 审核结果：合规/不合规
            note left: 不合规内容：\n结束当前轮次对话
        also 开启智能体对话
            Server -> AI : 开启智能体对话：语音识别结果 + 对话上下文 + 设备记忆
            AI --> Server : 生成回复文本
        end par
        par 大模型回复内容审核
            Server -> Audit : 大模型回复内容审核
            Audit --> Server : 审核结果：合规/不合规
            note left: 不合规内容：\n结束当前轮次对话
        also TTS生成
            Server -> TTS : 大模型回复转成音频
            TTS --> Server : 生成音频
        end par
    end
    Server -> Toy : TTS音频 + 下行事件指令
    Toy -> Toy : 执行事件指令 + 播放音频
    Toy -> Child : 交互反馈（语音/动作）   
else 校验不通过
    Server --> Toy : 拒绝未授权访问，终止交互
    Toy -> Child : 交互失败提示
end alt
@enduml
实现语音通话
操作步骤
代码示例
step1:建立websocket连接
发起建连请求时，在请求头（Header）中添加Authorization信息。Authorization的取值固定为Bearer ${Access Token}，用于joyInside OpenAPI 鉴权的访问密钥。将您将在准备工作中获取的访问令牌替换掉 ${Access Token} 后再发起请求。
import threading
import uuid
import websocket
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入自定义模块
from auth_token_demo import get_token
from config import BOT_ID
from joy_inside_py.api_config import URL_VOICE_CHAT
from joy_inside_py.audio_tool import send_audio
from joy_inside_py.event_handler import ping
from util.logger import logger

# 常量定义
BYTES_PER_MS = 16000 * 2 / 1000  # 16000Hz采样率，16bits=2bytes，1000ms
FRAME_MS = 120  # WebSocket一个数据帧的时长（毫秒）
BYTES_PER_FRAME = int(BYTES_PER_MS * FRAME_MS)  # 一个数据帧的大小（字节）
PCM_FILE_PATH = "../test.pcm"

class WebsocketHandler:
    sessionId = ${填入准备工作中获取的botid} + str(uuid.uuid4())
    requestId = str(uuid.uuid4())
    logger.info("requestId: %s", requestId)
    uid = ""

    def start(self, uid):
        self.uid = uid
        ws_url = "%s?botId=%s&sessionId=%s&requestId=%s" % ("wss://ws.joyinside.com/soulmate/voiceChat/v1", ${填入准备工作中获取的botid}, self.sessionId, self.requestId)

        ws = websocket.WebSocketApp(
            ws_url,
            header=[f"Authorization: Bearer " + ${准备工作中获取的访问令牌}],
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close
        )
        ws.run_forever()

    def on_open(self, ws):
        # 开始发送心跳
        threading.Thread(target=ping, args=(ws, self.uid)).start()
        # 发送音频
        send_audio(ws, self.uid)

    def send_audio(ws, uid):
        with open(PCM_FILE_PATH, 'rb') as f:
            index = 0
            while True:
                data = f.read(BYTES_PER_FRAME)
                if not data:
                    break

                # 判断是否是最后一次读取
                if len(data) < BYTES_PER_FRAME:
                    index = ~index  # 取反操作

                logger.info(f"序号: {index}, 音频字节数: {len(data)}")
                audio_base64 = base64.b64encode(data).decode('utf-8')
                params = {
                    "mid": str(uuid.uuid4()),
                    "contentType": "AUDIO",
                    "content": {
                        "audioBase64": audio_base64,
                        "index": index
                    },
                    "uid": uid
                }
                ws.send(json.dumps(params))
                index += 1
                time.sleep(FRAME_MS / 1000)

    def on_message(self, ws, message):
        logger.debug("Received: %s", message)

    def on_error(self, ws, error):
        logger.error("Error: %s", error)

    def on_close(self, ws, close_status_code, close_msg):
        logger.warning("WebSocket closed: %s", close_status_code, close_msg)
step2:发送和接收事件
通过 WebSocket 与 Agent 进行实时语音交互时，需要通过 WebSocket 接口发送和接收消息。成功连接后，设备端可以发送和接收代表文本、音频、配置更新等的事件。
常见问题websocket连接失败
问题排查
建立连接时必须保证 access token 在有效时间内
建立连接时传入sessionId，建议每次ws建连新生成uuid传入，用于实现多轮对话；
若使用同一个 botid 创建两个 websocket 连接则会出现设备互踢报错，互踢标识："eventType":"REPEAT_CLIENT_SESSION"
记忆紊乱
问题排查
上行事件 uid 参数请传递真实的用户 pin 等信息，或者不传递，禁止所有设备使用相同固定值（例如123456等），影响记忆功能的使用
用户pin在导航栏最下方【个人信息】中查看
（2）对话交互模式joyInside 支持自由对话模式和手动对话模式。在建立 websocket 连接时，通过 needManualCall 参数设置，默认为自由对话模式，若要使用手动对话模式，需将 needManualCall 设置为 true
自由对话模式：
@startuml 自由模式交互时序图

' 样式定义
skinparam sequenceArrowThickness 2
skinparam noteBackgroundColor #FFF3E0
skinparam noteBorderColor #FFB74D
skinparam participantBackgroundColor #F5F5F5
skinparam actorBackgroundColor #E8F5E8
skinparam arrowColor #333333

' 参与者定义
actor "用户" as User
participant "AI设备（终端）" as Device
participant "JoyInside云端服务" as Server

== 自由模式交互 ==

Device -> Server : 持续上传语音数据
activate Device
activate Server
Device -> Device : **AEC持续中**
Server -> Server : 云端处理（**VAD持续中**）

User -> Device : 开始对话
activate User
Device -> Device : **AEC持续中**
Device -> Server : 持续上传语音数据
Server -> Server : 云端处理（**VAD检测到对话开始**）
Server -> Server : 云端处理（**ASR识别中**）

User -> Device : 停止说话
deactivate User
Device -> Server : 持续上传语音数据
Server -> Server : 云端处理（**VAD检测到对话结束**）
Server -> Server : 云端处理（**ASR识别完成+Agent执行+TTS生成**）
Server --> Device : 下发回复音频与可执行指令
deactivate Server
Device --> User : 播放音频并执行指令
deactivate Device


' 支持语音打断的说明
note over User, Device
**支持语音打断**：
在云端处理或设备播放期间，
用户新语音输入可触发新一轮交互，
中断当前流程。
end note

@enduml

默认支持自由对话模式，云端支持 VAD+ASR
设备端收音必须支持音频输出回采，支持 AEC
打断逻辑：设备端接收云端发送的 CALL_AGENT_INTERRUPTED 事件进行打断处理
注意：
收到 CALL_AGENT_INTERRUPTED 事件后，设备端应该清空当前语音播放队列，准备播放新的 TTS 音频流
手动对话模式
@startuml 手动模式交互时序图

' 样式定义
skinparam sequenceArrowThickness 2
skinparam noteBackgroundColor #E3F2FD
skinparam noteBorderColor #90CAF9
skinparam participantBackgroundColor #F5F5F5
skinparam actorBackgroundColor #E8F5E8

' 参与者定义
actor "用户" as User
participant "AI设备（终端）" as Device
participant "JoyInside云端服务" as Server

== 手动模式交互 ==
User -> Device : 按住按键+开始对话
activate User
activate Device
Device -> Server : 上传语音
activate Server
Server -> Server : **云端处理**（ASR识别中）
User -> Device : 松开按键+结束对话
deactivate User
Device -> Server : 上传事件CLIENT_AUDIO_FINISH
Server -> Server : **云端处理**（ASR识别完成+Agent执行+TTS生成）
Server --> Device : 下发回复音频与可执行指令
deactivate Server
Device --> User : 播放音频并执行指令
deactivate Device

' 端侧VAD使用说明
note over User, Device
**端侧VAD使用**：
若端侧具备VAD功能，
可以用VAD的开始结束代替按键。
end note

@enduml

在 websocket 连接时，设置手动模式 needManualCall=true
音频发送结束时，必须发送 CLIENT_AUDIO_FINISH 事件
需要打断 TTS 音频播放时，必须发送 CLIENT_INTERRUPT 事件
注意：
新一轮对话开始时，如果TTS还在输出，必须 CLIENT_INTERRUPT 打断，否则轮次判定异常
class WebsocketHandler:
    sessionId = BOT_ID + str(uuid.uuid4())
    requestId = str(uuid.uuid4())
    print("requestId:", requestId)
    uid = ""

    def start(self, uid):
        self.uid = uid
        ## 自由对话模式
        ws_url = "wss://ws.joyinside.com/soulmate/voiceChat/v1?botId=%s&sessionId=%s&requestId=%s" % ( BOT_ID, self.sessionId, self.requestId)
        ## 手动对话模式        
        ws_url = "wss://ws.joyinside.com/soulmate/voiceChat/v1?botId=%s&sessionId=%s&requestId=%s&needManualCall=true" % ( BOT_ID, self.sessionId, self.requestId)

        ws = websocket.WebSocketApp(
            ws_url,
            header=[f"Authorization: Bearer " + get_token()],
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close
        )
        ws.run_forever()

（3）对话音频设置上行音频设置
pcm音频格式
采样率支持 16k 、24k 、32k（默认为16k）
pcm每次发送不能超过 300 ms
opus音频格式
通过 CLIENT_VOICE_CHAT_UPDATE 事件进行设置
将 audio.input.codec 参数设置为 opus
采样率支持 16k 、24k 、32k（默认为16k）
单帧长不能超过120ms，字节数不拿超过480字节，建议帧长保持60ms每帧
多个固定长度拼接帧需将 audio.input.frameSize 参数设置为每帧的字节长度，输入音频拼接不能超过 300ms
注意：
1、CLIENT_VOICE_CHAT_UPDATE每次连接只用最开始发送一次，否则会导致对话被打断，如果对话中需要切换角色也需要发送CLIENT_VOICE_CHAT_UPDATE事件
2、一定要收到“更新语音对话配置成功”事件，CLIENT_VOICE_CHAT_UPDATE事件才算成功
3、均匀发送音频包，间隔应该是音频时长，否则会回复延时异常
下行音频设置
pcm音频格式
采样率支持 16k 、24k 、32k（默认为16k）
TTS单帧时长设置
不设置，默认帧时长【360～720】ms
通过 CLIENT_VOICE_CHAT_UPDATE 事件中 audio.output.frameSizeMs 参数进行设置，帧时长数值范围为【60-120】ms
opus音频格式
采样率支持 16k 、24k 、32k（默认为16k）
TTS单帧时长设置
不设置，默认时长60ms
通过 CLIENT_VOICE_CHAT_UPDATE 事件中 audio.output.frameSizeMs 参数进行设置，帧时长数值可选值为 10、20、40、60 ms
支持CBR编码模型（每帧固定字节数），默认为VBR编码模型。可通过 CLIENT_VOICE_CHAT_UPDATE 事件中 audio.output.enableOpusCbr 参数进行设置
mp3音频格式
采样率支持 16k 、24k 、32k（默认为16k）
目前TTS生成未支持流式，也不支持切分
注意：
1、确保端上解码和配置的音频格式相匹配
2、确保端上内存空间足够，否则不要使用mp3格式，如果内存不够缓存音频片段，会导致丢包
3、下发的opus裸流是单声道
上行下行音频使用二进制
确定是否二进制传输如果需要按照binary使用，CLIENT_VOICE_CHAT_UPDATE 事件中传入 audio.binary=true 开启二进制传输
使用二进制传输，传入音频时使用 webSocket send(bytes:byteString) 上送音频流，监听同理。
使用二进制传输，二进制通道仅用于音频输入输出，代替了上行事件-流式上传音频和下行事件-增量流式音频，其他事件正常用 text 消息交互
注意：
若响应结果为：{"code":400,"msg":"audio binary not support."}
表示未启用二进制格式，但在WebSocket消息中传入bytes类型消息
def update_config(ws, uid):
    params = {
        "mid": str(uuid.uuid4()),
        "uid": uid,
        "contentType": "EVENT",
        "content": {
            "eventType": "CLIENT_VOICE_CHAT_UPDATE",
            "eventData": {
                "audio": {
                    "binary": True, #启用配置
                    "input": {
                        "codec": "pcm", #上行音频格式是pcm
                        "sampleRate": "16000", #采样率是16000
                    },
                    "output": {
                        "codec": "opus",#下发音频格式opus
                        "enableOpusCbr": True,#下发音频格式的opus是CBR格式
                        "sampleRate": "16000",#采样率是16000
                        "frameSizeMs": "40",#流式每次下发音频长度为40ms
                    }
                }
            }
        }
    }
    ws.send(json.dumps(params))
（4）其他指令事件上行事件更新语音对话配置：更新当前会话的语音对话配置
{
    "mid": "24279824-8def-48c6-8d1c-ea8ec3aa50ac",
    "contentType": "EVENT",
    "content": {
        "eventType": "CLIENT_VOICE_CHAT_UPDATE",
        "eventData": {
            "audio": {
                "binary": true,
                "input": {
                    "codec": "pcm",
                    "sampleRate": "16000"
                },
                "output": {
                    "codec": "opus",
                    "sampleRate": "16000",
                    "frameSizeMs": "40"
                }
            }
        }
    }
}
流式上传音频：流式向服务端提交音频片段
{
  "mid": "f70e8955-8b39-4ae8-bba1-2bea4aa6c50b",
  "contentType": "AUDIO",
  "uid": "用户id",
  "content": {
    "audioBase64": "PwAVAOv/qP9i/yP/Df8O/wP/Cv8X/wr/8v7X/....", // 音频数据的Base64编码字符串
    "index": 1
  }
}

心跳发起：发送PING包维持长链接，建议30秒发送间隔
{
  "mid": "f70e8955-8b39-4ae8-bba1-2bea4aa6c50b",
  "contentType": "PING",
  "uid": "用户id"
}
打断智能体输出：发送此事件，取消智能体正在进行的语音对话；手动模式下打断语音回复需要传入
{
  "mid": "24279824-8def-48c6-8d1c-ea8ec3aa50ac",
  "contentType": "EVENT",
  "uid": "终端用户id",
  "content": {
    "eventType": "CLIENT_INTERRUPT"
  }
}
结束音频上传：发送此事件，通知服务端结束音频上传，仅手动模式下需要传入
{
  "mid": "24279824-8def-48c6-8d1c-ea8ec3aa50ac",
  "contentType": "EVENT",
  "uid": "终端用户id",
  "content": {
    "eventType": "CLIENT_AUDIO_FINISH"
  }
}
发送对话内容：发送文本与智能体对话，提交文本内容后会流式回复文本内容和流式音频
{
  "mid": "f70e8955-8b39-4ae8-bba1-2bea4aa6c50b",
  "contentType": "TEXT",
  "uid": "用户id",
  "content": {
    "input": "讲个故事吧"
  }
}

请求音频合成：提交事件后，主动提交文字用来进行语音合成，提交的信息不会触发智能体，只会流式生成语音合成的音频片段。提交事件的时候如果智能体正在输出语音会被中断输出。
{
  "mid": "f70e8955-8b39-4ae8-bba1-2bea4aa6c50b",
  "contentType": "EVENT",
  "uid": "用户id",
  "content": {
    "eventType": "CLIENT_INPUT_TEXT_TO_SPEECH",
    "eventData": {
      "text": "需要合成的文本"
    }
  }
}
主动触发对话：发送此事件，触发智能体执行希望指令
{
  "mid": "f70e8955-8b39-4ae8-bba1-2bea4aa6c50b",
  "contentType": "ACTIVITY",
  "content": {
    "activityType": "VOICE_CHAT_TRIGGER",
    "kvData": {
        // 自定义事件消息体
    }
  }
}
主动更新对话上下文：更新对话上下文内容，短期记忆在对话链路中，在提示词中使用，使用方法参考上文【其他- 自定义变量使用】。注意：使用此功能，需向JoyInside运营团队申请权限。
{
    "code": 200,
    "requestId": "1",
    "mid": "1",
    "contentType": "ACTIVITY",
    "content": {
        "activityType": "CLIENT_UPDATE_CHAT_CONTEXT",
        "effectiveTimeMinutes": 5, // 记忆XX分钟，取值范围：[1~1440] 
        "kvData": {
            // 自定义拓展信息
        }
    }
}
下行事件默认语音对话配置：对话接口成功建立连接，服务端会发送服务端默认语音对话配置
{
  "code": 200,
  "msg": "Event success",
  "requestId": "a4595acb-de6c-4ac9-92b2-8fa59a7f91f7",
  "mid": null,
  "contentType": "EVENT",
  "content": {
    "roundId": "",
    "eventType": "CFG_BOT_EVENT",
    "eventData": {
      "timbre": {
        "voiceName": "小犀",
        "voiceSpeed": 1.0
      },
      "tts": {
        "aue": "pcm",
        "bit": 16,
        "channels": 1,
        "sr": "16000"
      },
      "deviceModel": "UNKNOWN",
      "deviceId": "UNKNOWN"
    }
  },
  "t": 1749117478297
}

更新语音对话配置成功：上行数据-更新语音对话配置 更新完成后，通知当前会话语音对话配置
{
    "code": 200,
    "msg": "Event success",
    "requestId": "222b0306-4e95-4163-9683-94f8c29609bf",
    "mid": "197211f7-2587-4d72-8504-6268616533ec",
    "contentType": "EVENT",
    "content": {
        "eventType": "SERVER_VOICE_CHAT_UPDATED",
        "eventData": {
            "audio": {
                "binary": true,
                "input": {
                    "codec": "pcm",
                    "sampleRate": "16000"
                },
                "output": {
                    "codec": "opus",
                    "sampleRate": "16000",
                    "frameSizeMs": "40"
                }
            }
        }
    },
    "t": 1752724083510
}
心跳响应：响应上行PING包
{
  "code": 200,
  "msg": "Event success",
  "requestId": "a4595acb-de6c-4ac9-92b2-8fa59a7f91f7",
  "mid": "a4595acb-de6c-4ac9-92b2-8fa59a7f91f7_2",
  "contentType": "PONG",
  "t": 1749117488694
}
音频识别内容：流式语音识别结果
{
  "code": 200,
  "msg": "ASR success",
  "requestId": "08ddd338-fd5b-4572-b03a-43974dc145db",
  "contentType": "ASR",
  "uid": "终端用户id",
  "mid": "c673b518375a4c23aeab8cb8458994d6",
  "content": {
    "text": "语音测试，给我个结果",
    "textType": "IS_FINAL",
    "lang": "普通话"
  },
  "t": 1745507675867
}
智能体对话开始：表示根据流式语音识别结果开启智能体对话
{
  "code": 200,
  "msg": "Event success",
  "requestId": "08ddd338-fd5b-4572-b03a-43974dc145db",
  "contentType": "EVENT",
  "uid": "终端用户id",
  "mid": "c673b518375a4c23aeab8cb8458994d6",
  "content": {
    "roundId": "b1c9fc68-01c4-48b4-ba79-a8440dc9a9fa_222726_1",
    "eventType": "CALL_AGENT_START_EVENT",
    "eventData": {
      "input": "语音测试，给我个结果",
      "startTime": 1745507675867
    },
    "t": 1745507675867
  }
}
智能体对话忽略：表示根据流式语音未识别结果不开启智能体对话
{
  "code": 200,
  "msg": "Event success",
  "requestId": "a4595acb-de6c-4ac9-92b2-8fa59a7f91f7",
  "mid": null,
  "contentType": "EVENT",
  "content": {
    "roundId": "a4595acb-de6c-4ac9-92b2-8fa59a7f91f7_1",
    "eventType": "EMPTY_CONTENT",
    "eventData": {
      "startTime": 1749117482960
    }
  },
  "t": 1749117482960
}
智能体回复文本：智能体的回复文本
{
  "code": 200,
  "msg": "LLM success",
  "requestId": "a4595acb-de6c-4ac9-92b2-8fa59a7f91f7",
  "mid": "a4595acb-de6c-4ac9-92b2-8fa59a7f91f7_2",
  "contentType": "AGENT",
  "content": {
    "roundId": "a4595acb-de6c-4ac9-92b2-8fa59a7f91f7_2",
    "role": "assistant",
    "content": "嘿！你好呀，",
    "reasoningContent": "",
    "finishReason": ""
  },
  "t": 1749117487494
}
智能体回复流式音频：TTS音频，智能体回复文本转音频后，流式下发
{
  "code": 200,
  "msg": "TTS success",
  "requestId": "a4595acb-de6c-4ac9-92b2-8fa59a7f91f7",
  "mid": "a4595acb-de6c-4ac9-92b2-8fa59a7f91f7_2",
  "contentType": "TTS",
  "content": {
    "roundId": "a4595acb-de6c-4ac9-92b2-8fa59a7f91f7_2",
    "audioBase64": "UklGRiQAAABXQVZFZm10IBAAAAABAAEARKwAAIhYAQACABAAZGF0YQAAAAA...",
    "audioAue": "mp3",
    "audioDuration": 2000,
    "finish": false
  },
  "t": 1749117488653
}

语音音频回复完成：TTS音频下发完成
{
  "code": 200,
  "msg": "Event success",
  "requestId": "551cc928-a9bb-464e-9ef0-aa7366b170a9",
  "mid": "551cc928-a9bb-464e-9ef0-aa7366b170a9_211532_1",
  "contentType": "EVENT",
  "content": {
    "roundId": "551cc928-a9bb-464e-9ef0-aa7366b170a9_211532_1",
    "eventType": "TTS_COMPLETE",
    "eventData": {
      "time": 1752758135335
    }
  },
  "t": 1752758135335
}
语音当轮对话完成：表示当轮对话完成
{
  "code": 200,
  "msg": "Event success",
  "requestId": "a4595acb-de6c-4ac9-92b2-8fa59a7f91f7",
  "mid": "a4595acb-de6c-4ac9-92b2-8fa59a7f91f7_2",
  "contentType": "EVENT",
  "content": {
    "roundId": "a4595acb-de6c-4ac9-92b2-8fa59a7f91f7_2",
    "eventType": "COMPLETE",
    "eventData": {
      "time": 1749117488694
    }
  },
  "t": 1749117488694
}

增量文本主动回复：智能体的主动对话文本，如果配置了静默推送会触发
{
  "code": 200,
  "msg": "LLM success",
  "requestId": "a4595acb-de6c-4ac9-92b2-8fa59a7f91f7",
  "mid": "a4595acb-de6c-4ac9-92b2-8fa59a7f91f7_2",
  "contentType": "ACTIVITY",
  "content": {
    "roundId": "a4595acb-de6c-4ac9-92b2-8fa59a7f91f7_2",
    "role": "assistant",
    "content": "嘿！你好呀，",
    "reasoningContent": "",
    "finishReason": ""
  },
  "t": 1749117487494
}
智能体打断事件：自由对话模式下，客户端收到智能体打断事件之后，需要打断正在播放的TTS音频流；准备播放新的音频流
{
  "code": 200,
  "msg": "Event success",
  "requestId": "XXXX",
  "mid": "XXX",
  "contentType": "EVENT",
  "content": {
    "roundId": "XXX",
    "eventType": "CALL_AGENT_INTERRUPTED",
    "eventData": {
      "startTime": 1763968984181
    }
  },
  "t": 1763968984181
}
自定义事件：各种自定义指令与非标准功能的下行事件
{
    "code": 200,
    "msg": "Event success",
    "requestId": "d45ed439-3fab-4b0d-a6ab-a4662e505d96",
    "contentType": "EVENT",
    "content": {
        "roundId": "d45ed439-3fab-4b0d-a6ab-a4662e505d96_141008_7",
        "eventType": "自定义指令类型",
        "eventData": {
            "msg": "自定义指令事件",
            "data": {
                
            },
            "type": "自定义指令类型"
        }
    },
    "t": 1766124655205
}
指令事件：用于设备控制类指令，例如控制音量调节，属于自定义事件的子类
{
    "code": 200,
    "msg": "Event success",
    "requestId": "1",
    "mid": "1",
    "contentType": "EVENT",
    "content": {
        "roundId": "0_1",
        "eventType": "CALL_SKILL_EVENT",
        "eventData": {
            "msg": "指令事件",
            "type": "CALL_SKILL_EVENT",
            "data": {
                "args": {
                    "slotKey": "slotValue"
                },
                "intentClassify": "LIGHT_UP"
            }
        }
    }
}
正常语音对话一个轮次包含事件
上行事件：
流式上传音频：设备端音频持续上传
下行事件：
音频识别内容
智能体对话开始
智能体回复文本
智能体回复流式音频
语音音频回复完成
语音当轮对话完成
特殊功能接入系统技能-有声书端侧对接连续对话版本对接
一、端侧修改概览1.1. 概述i. 建联增加参数
ws连接时增加参数：feature=AUDIO_BOOK_V2表示开启有声书功能
ii. 开播
有声书资源为mp3链接，需要流式播放
接收到服务端开播事件和开播串场词后，等待开播串场词播放完成（开播串场词为正常交互tts，会先于开播事件下发），加载开播事件中的资源地址播放有声书，同时发送上行开播事件反馈给服务端
接收到开播事件后，开始执行心跳上行事件，直到服务端主动上报停播或者接收到客户端停播事件时，停止心跳上行事件
iii. 停播
当服务端下发停播事件后，客户端需结束有声书播放，且上行停播事件，将章节播放进度等参数上行至服务端
资源自动播放结束时，上行停播事件（progress=totalLength，finish=true），服务端自动判断需要续播，并下发新的开播事件（同开播）或【完播】下发完播tts（同正常交互tts）
iv. 播控
资源切换 a. 有声书开播时，支持输入：暂停播放、上/下一集、重播、跳集等播控事件。但是无法进行点播、闲聊等事件
1.2. 相关事件i. 下行
开播
a. 用户语音开播、完播切换资源、播控切换资源
停播
a. 相关场景：本期不涉及
ii. 上行
有声书开播和停止时发送上行事件同步播放状态 a. 开播
开始播放资源后状态同步 b. 停播
停止播放资源后状态同步
有声书开播、心跳、停播事件外还需关注的事件：
contentType=EVENT，content.eventType=TTS_SENTENCE_START，接收到此事件，表示后续将会下行TTS事件。（有声书场景一定会有串场词TTS，但是为了扩展性，尽量使用此事件，来判断是否有TTS）
contentType=TTS，接收到此事件，表示需要音频播放TTS资源。此事件会多次下行，需按照多个TTS事件下行顺序，顺序播放content.audioBase64。结合TTS_COMPLETE，控制有声书播放时机，即接收到TTS_COMPLETE，且所有TTS音频播放完成后，开始播放有声书资源
contentType=EVENT，content.eventType=TTS_COMPLETE，接收到此事件，表示TTS资源已全部下发完成
contentType=AGENT，此事件为串场词明文，可当字幕展示。此事件会多次下行，按顺序拼接content.content，直到finishReason为“stop”结束
二、端侧交互序列图2.1. 开播序列序列图展示
2.2. 完播续播序列序列图展示
序列图流程说明
1 @startuml 有声书纯语音交互序列图
2 actor 用户 as User
3 participant 客户端 as Client #LightBlue
4 participant 服务端 as Server #LightGreen
5 Client -> User: 播放中
6 == 资源完播 ==
7 Client -> Server: 播放完成发送停播事件\nfinish=true(上行事件)
8 Server -> Server: 查找续播资源
9 alt 章节完播
10 Server -> Server: 生成续播串场词
11 Server -> Server: 从资源库获取对应章节信息及音频URL
12 Server -> Client: 播控串场词(TTS)
13 Server -> Client: 播放资源(下行事件)
14 Client -> User: 播放串场词
15 Client -> Client: 串场词播放完毕后执行有声书播放逻辑
16 Client -> User: 播放有声书
17 Client -> Server: 开播上报(上行事件)
18 else 整本完播
19 Server -> Client: 完播提示语(TTS)
20 Client -> User: 播放完播提示语
21 end
22 note over Server, User: 服务端收到播放停止事件并判断完播状态,若单章完播下发续播TTS和续播资源,若整本完播下发完播提示TTS
23 @endumlCopy to clipboardErrorCopied
2.3. 停播续播序列序列图展示
序列图流程说明
1 @startuml 有声书纯语音交互序列图
2 actor 用户 as User
3 participant 客户端 as Client #LightBlue
4 participant 服务端 as Server #LightGreen
5 Client -> User: 播放中
6 == 播放中停止 ==
7 User -> Client: 语音唤醒:"你好东东"
8 Client -> Client: 唤醒语音识别模块
9 Client -> User: TTS:"我在"
10 Client -> Server: 停止播放(上行事件)
11 note over User, Server: 播放中唤醒停止播放, 并发送停播上行事件
12 alt 场景1: 停止命令
13 User -> Client: 语音指令:"停止播放"
14 Client -> Server: 推送语音
15 Server -> Server: \n1. 调用ASR
16 Server -> Server: 2. 解析指令:停止播放\n3. 生成暂停播放串场词
17 Server -> Client: 停播串场词(TTS)
18 Server -> Client: 停止播放指令(下行事件)
19 Client x-x Client: 执行停止播放逻辑
20 Client x-> Server: 播放进度上报（上行事件）
21 Client -> User: 播放串场词
22 note over Client, Server: 若唤醒时已执行停止播放逻辑, 此处客户端播放停播串场词即可
23 else 场景2: 播放命令
24 User -> Client: 语音指令:"播放下一章/继续播放"
25 Client -> Server: 推送语音
26 Server -> Server: \n1. 调用ASR
27 Server -> Server: 2. 解析指令\n3. 生成播放串场词
28 Server -> Server: 4. 从资源库获取对应章节信息及音频URL
29 Server -> Client: 播放串场词(TTS)
30 Server -> Client: 播放资源(下行事件)
31 Client -> Client: 执行音频停止播放逻辑
32 Client -> Server: 播放进度上报(上行事件)
33 Client -> User: 播放串场词
34 Client -> Client: 串场词播放完毕后执行有声书播放逻辑
35 Client -> User: 播放有声书
36 Client -> Server: 开播上报(上行事件)
37 Server -> Server: 记录开播状态
38 note over Server, Client: 若唤醒时已执行停止播放逻辑, 此处客户端只执行串场词播报和新资源播放\n服务端确保先推送串场词(TTS), 后下发待播URL(下行事件)
39 else 场景3: 语音交互
40 note over Server, User: 正常语音交互逻辑
41 end
42 @endumlCopy to clipboardErrorCopied
三. 协议3.1上行事件a. 有声书事件contentType统一使用AUDIO_BOOK
字段名称
类型
必选
说明
mid
string
是
请求唯一标识符，用于追踪每次消息请求和响应的对应关系
uid
string
否
用户唯一标识
contentType
string
是
固定为AUDIO_BOOK
content
object
是
事件数据载体
t
long
是
时间戳
-content.eventType
string
是
上行事件类型
-content.eventData
object
是
语音对话配置项，见表格说明
i. 开始播放有声书
端上开始播放有声书时发送上行事件
-content.eventType: AUDIO_BOOK_PLAY
-content.eventData
字段名称
类型
必选
说明
bookId
string
是
当前播放书id
chapterId
string
是
当前播放章节id
ii. 停止播放有声书
有声书停止播放时必须发送该事件并提交当前播放进度，也可通过该事件主动停止播放 a. 播放再次唤醒退出播放状态进入对话状态 b. 资源播放完成
-content.eventType: AUDIO_BOOK_STOP
-content.eventData
字段名称
类型
必选
说明
bookId
string
是
当前播放书id
chapterId
string
是
当前播放章节id
progress
long
是
播放进度（已播长度，单位：秒）
finish
boolean
是
false-未完播
true-完播
iii. 播放有声书心跳
有声书播放过程中，通过定时ping pang维持心跳状态，心跳间隔≤2S
当接收到AUDIO_BOOK_PLAY下行事件后，立刻开始ping pang
字段名称
类型
必选
说明
mid
string
是
请求唯一标识符，用于追踪每次消息请求和响应的对应关系
uid
string
否
用户唯一标识
contentType
string
是
固定为AUDIO_BOOK
content
object
是
事件数据载体
t
long
是
时间戳
-content.eventType
string
是
AUDIO_BOOK_PING
-content.eventData
string
是
{}
3.2 下行事件字段名称
类型
必选
说明
code
string
是
响应状态码，200表示成功，其他值表示错误
msg
string
是
状态描述信息
requestId
string
是
请求唯一标识符
mid
string
是
请求唯一标识符，对应上行请求唯一标识符
uid
string
否
用户唯一标识
t
long
是
服务端处理时间戳（毫秒级）
contentType
string
是
固定为AUDIO_BOOK
content
object
是
事件数据载体
-content.roundId
string
是
请求轮次index
-content.eventType
string
是
事件类型
-content.eventData
object
是
对话开始响应，见表格说明
a. 播放有声书
播放有声书事件会伴随串场词TTS，与正常语音交互相同，需要先播放串场词后开始播放有声书（串场词会先于有声书播放事件下发）
-content.eventType: AUDIO_BOOK_PLAY
-content.eventData
字段名称
类型
必选
说明
bookId
string
是
当前播放书id
bookName
string
是
当前播放书名
chapter
string
是
当前播放章节名
chapterId
string
是
当前播放章节id
chapterName
string
是
当前播放章节名
progress
long
否
播放进度 已播长度
totalLength
long
是
音频总长
audioURL
string
是
播放地址
imageURL
string
否
有声书封面地址
b. 停止播放
停止播放有声书事件中会伴随播报TTS，与正常语音交互相同
停止播放后必须发送停止上行事件，同步播放进度，结束播放状态
-content.eventType: AUDIO_BOOK_STOP
-content.eventData
字段名称
类型
必选
说明
bookId
string
是
当前播放书id
chapterId
string
是
当前播放章节id
c. 心跳下行
字段名称
类型
必选
说明
mid
string
是
请求唯一标识符，用于追踪每次消息请求和响应的对应关系
uid
string
否
用户唯一标识
contentType
string
是
固定为AUDIO_BOOK
content
object
是
事件数据载体
t
long
是
时间戳
-content.eventType
string
是
AUDIO_BOOK_PONG
-content.eventData
string
是
{}
按键对话版本对接
一、端侧修改概览1.1. 概述i. 建联增加参数
ws url增加参数feature=AUDIO_BOOK表示开启有声书功能
ws url增加参数clientType=AUDIO_BOOK表示当前处于有声书界面，建联时播放有声书欢迎语
ii. 开播
有声书资源为mp3链接，需要流式播放
接收到服务端开播事件和开播串场词后，等待开播串场词播放完成（开播串场词为正常交互tts，会先于开播事件下发），加载开播事件中的资源地址播放有声书，同时发送上行开播事件反馈给服务端。停止端上收音避免播放被打断，直到再次识别到唤醒。
当接收到服务端下行的AUDIO_BOOK_PLAY开播事件，开启ws心跳：Ping、Pang
iii. 停播
播放中识别到唤醒时停止资源播放，并开启收音，发送上行停播事件给服务端同步播放进度
资源播放结束时发送停播事件(finish为true)，服务端判断已完结将自动出发徐波，下发新的开播事件，同时下发完播tts（同正常交互tts）
iv. 播控
资源切换 a. 本期需求播放时暂停收音，再次唤醒时先停播并开启收音，因此切换书目、切换章节、复播均等同于开播操作，不必另行处理。
1.2. 相关事件i. 下行
开播
a. 用户语音开播、完播切换资源、播控切换资源
停播
a. 相关场景：本期不涉及
ii. 上行
有声书开播和停止时发送上行事件同步播放状态 a. 开播
开始播放资源后状态同步 b. 停播
停止播放资源后状态同步
有声书开播、心跳、停播事件外还需关注的事件：
contentType=EVENT，content.eventType=TTS_SENTENCE_START，接收到此事件，表示后续将会下行TTS事件。（有声书场景一定会有串场词TTS，但是为了扩展性，尽量使用此事件，来判断是否有TTS）
contentType=TTS，接收到此事件，表示需要音频播放TTS资源。此事件会多次下行，需按照多个TTS事件下行顺序，顺序播放content.audioBase64。结合TTS_COMPLETE，控制有声书播放时机，即接收到TTS_COMPLETE，且所有TTS音频播放完成后，开始播放有声书资源
contentType=EVENT，content.eventType=TTS_COMPLETE，接收到此事件，表示TTS资源已全部下发完成
contentType=AGENT，此事件为串场词明文，可当字幕展示。此事件会多次下行，按顺序拼接content.content，直到finishReason为“stop”结束
二、端侧交互序列图2.1. 开播序列序列图展示
2.2. 完播续播序列序列图展示
2.3. 停播续播序列序列图展示
三. 协议3.1 上行事件a. 有声书事件contentType统一使用AUDIO_BOOK
字段名称
类型
必选
说明
mid
string
是
请求唯一标识符，用于追踪每次消息请求和响应的对应关系
uid
string
否
用户唯一标识
contentType
string
是
固定为AUDIO_BOOK
content
object
是
事件数据载体
t
long
是
时间戳
-content.eventType
string
是
上行事件类型
-content.eventData
object
是
语音对话配置项，见表格说明
i. 开始播放有声书
端上开始播放有声书时发送上行事件
-content.eventType: AUDIO_BOOK_PLAY
-content.eventData
字段名称
类型
必选
说明
bookId
string
是
当前播放书id
chapterId
string
是
当前播放章节id
ii. 停止播放有声书
有声书停止播放时必须发送该事件并提交当前播放进度，也可通过该事件主动停止播放 a. 播放再次唤醒退出播放状态进入对话状态 b. 资源播放完成
-content.eventType: AUDIO_BOOK_STOP
-content.eventData
字段名称
类型
必选
说明
bookId
string
是
当前播放书id
chapterId
string
是
当前播放章节id
progress
long
是
播放进度（已播长度，单位：秒）
finish
boolean
是
false-未完播
true-完播
iii. 播放有声书心跳
有声书播放过程中，通过定时ping pang维持心跳状态，心跳间隔≤2S
当接收到AUDIO_BOOK_PLAY下行事件后，立刻开始ping pang
字段名称
类型
必选
说明
mid
string
是
请求唯一标识符，用于追踪每次消息请求和响应的对应关系
uid
string
否
用户唯一标识
contentType
string
是
固定为AUDIO_BOOK
content
object
是
事件数据载体
t
long
是
时间戳
-content.eventType
string
是
AUDIO_BOOK_PING
-content.eventData
string
是
{}
3.2 下行事件字段名称
类型
必选
说明
code
string
是
响应状态码，200表示成功，其他值表示错误
msg
string
是
状态描述信息
requestId
string
是
请求唯一标识符
mid
string
是
请求唯一标识符，对应上行请求唯一标识符
uid
string
否
用户唯一标识
t
long
是
服务端处理时间戳（毫秒级）
contentType
string
是
固定为AUDIO_BOOK
content
object
是
事件数据载体
-content.roundId
string
是
请求轮次index
-content.eventType
string
是
事件类型
-content.eventData
object
是
对话开始响应，见表格说明
a. 播放有声书
播放有声书事件会伴随串场词TTS，与正常语音交互相同，需要先播放串场词后开始播放有声书（串场词会先于有声书播放事件下发）
-content.eventType: AUDIO_BOOK_PLAY
-content.eventData
字段名称
类型
必选
说明
bookId
string
是
当前播放书id
bookName
string
是
当前播放书名
chapter
string
是
当前播放章节名
chapterId
string
是
当前播放章节id
chapterName
string
是
当前播放章节名
progress
long
否
播放进度 已播长度
totalLength
long
是
音频总长
audioURL
string
是
播放地址
imageURL
string
否
有声书封面地址
b. 停止播放
停止播放有声书事件中会伴随播报TTS，与正常语音交互相同
停止播放后必须发送停止上行事件，同步播放进度，结束播放状态
-content.eventType: AUDIO_BOOK_STOP
-content.eventData
字段名称
类型
必选
说明
bookId
string
是
当前播放书id
chapterId
string
是
当前播放章节id
c. 心跳下行
字段名称
类型
必选
说明
mid
string
是
请求唯一标识符，用于追踪每次消息请求和响应的对应关系
uid
string
否
用户唯一标识
contentType
string
是
固定为AUDIO_BOOK
content
object
是
事件数据载体
t
long
是
时间戳
-content.eventType
string
是
AUDIO_BOOK_PONG
-content.eventData
string
是
{}
自定义技能-技能扩展开发示例1、授权方式使用令牌授权方式。
2、接口定义流式接口，支持输出消息内容、指令内容。
基础信息：
请求方式
POST
请求地址
示例：https://api.xxx.com/v1/workflow?workflow_id=xxxx
接口说明
响应方式为流式响应，按需添加的query参数需拼接在请求地址中。
Header由接口方配置。
参数
取值
说明
token参数名
(如：Authorization)
token值
(如：Bearer $Access_Token)
用于验证客户端身份的访问令牌。
Content-Type
application/json
解释请求正文的方式。
Query参数由接口方配置，按需添加多个query参数，须事先拼接在配置的请求接口地址中。
Body由平台方自动填入平台默认参数。
参数
类型
是否必选
说明
parameters
Map[String][Object|List]

必选
目前仅支持以下字段：
request_id：String 类型，表示请求ID。
session_id：String 类型，表示会话ID。
round_id: String 类型，轮次ID。
bot_id: String 类型，bot ID。
app_id: String 类型，应用ID。
lang: String 类型，当前对话语种。
long_term_memory: String 类型，长期记忆内容。
messages: List<Conversation> 列表类型，历史消息，包含当前用户轮的input。
input: String 类型，用户query。
lang: String 类型，对话使用的语言。
system_time: String 类型，当前时间，格式 "yyyy-MM-dd HH:mm:00"。 
location： String类型，地点。
rag_recall_result：String类型，检索结果。

其中：
Conversation 定义： {
        String role;   // 角色 "user", "assistant"
        String content;  // 内容
}
返回结果在流式响应中，接口返回数据时，须先返回 Message 事件类型消息，再返回 Instruction 事件类型消息[如有]，顺序不可乱。
事件 ID（id）默认从 0 开始计数，以包含 event: Done 的事件为结束标志。
Message 事件的消息 ID 默认从 0 开始计数，以包含 node_is_finish : true 的事件为结束标志[可选]。
参数名
参数类型
是否必选
参数描述
id
Integer
是
此消息在接口响应中的事件 ID，ID值自定义，建议以 0 开始，处理消息时不校验。
event
String
是
当前流式返回的数据包事件。包括以下类型：
Message：输出消息，例如输出节点、结束节点的输出消息[可选]。
Error：报错。
Done：结束。表示执行结束。
Instruction：指令。输出指令，一次输出一个完整的指令。
data
Object
是
事件内容。各个 event 类型的事件内容格式不同。
事件定义1：Message 事件Message 事件中，data 的结构如下：
参数名
参数类型
是否必选
参数描述
content
String 
是
流式输出的消息内容，将输出到终端设备。
node_title
String
否
输出消息的节点名称，例如输出节点、结束节点。
node_seq_id
String
否
此消息在节点中的消息 ID，从 0 开始计数，例如输出节点的第 5 条消息。
node_is_finish
Boolean
否
当前消息是否为此节点的最后一个数据包。
node_id
String
否
输出消息的节点 ID。
事件定义2：Instruction 事件Instruction 事件中，data 的结构自定义，data内容将直接透传到终端设备。
事件定义3：Error 事件Error 事件中，data 的结构如下：
参数名
参数类型
是否必选
参数描述
error_code
Integer
是
调用状态码：
0 表示调用成功。
其他值表示调用失败。
error_message
String 
是
错误信息。
示例请求示例curl --location --request POST 'https://api.xxx.com/v1/workflow?workflow_id=12345' \
--header 'Authorization: Bearer pat_fhwefweuk****' \
--header 'Content-Type: application/json' \
--data-raw '{
    "parameters": {
        "bot_id": "122333444",
        "input": "讲个小故事"
    }
}'
响应示例id: 0
event: Message
data: {"content":"msg","node_is_finish":false,"node_seq_id":"0","node_title":"Message"}

id: 1
event: Message
data: {"content":"为","node_is_finish":false,"node_seq_id":"1","node_title":"Message"}

id: 2
event: Message
data: {"content":"什么小明要带一把尺子去看电影？\n因","node_is_finish":false,"node_seq_id":"2","node_title":"Message"}

id: 3
event: Message
data: {"content":"为他听说电影很长，怕","node_is_finish":false,"node_seq_id":"3","node_title":"Message"}

id: 4
event: Message
data: {"content":"坐不下！","node_is_finish":true,"node_seq_id":"4","node_title":"Message"}

id: 5
event: Done // 全部输出结束时，必须发送该事件。
data: {}
id: 0
event: Instruction
data: {...}  // 自定义结构，透传至终端设备
id: 0
event: Error
data: {"error_code":4000,"error_message":"Request parameter error"} // 自定义错误信息
