import clr
clr.AddReference('Kingdee.BOS')
clr.AddReference('Kingdee.BOS.Core')
clr.AddReference('Kingdee.BOS.DataEntity')
clr.AddReference('Kingdee.BOS.ServiceHelper')
clr.AddReference('Newtonsoft.Json')

from System import *
from Kingdee.BOS.Core import *
from Kingdee.BOS.DataEntity import *
from Kingdee.BOS.ServiceHelper import BusinessDataServiceHelper
from Kingdee.BOS.ServiceHelper import DBServiceHelper
from Newtonsoft.Json import JsonConvert

# 有效结算方式数组
VALID_PM = ["10", "11", "JSFS01_SYS", "JSFS06_SYS", "JSFS07_SYS", "JSFS09_SYS"]
# 需要票据流水号的结算方式数组
NEED_BILL_PM = VALID_PM[-3:]
# decimal 0 常量
ZERO = Decimal(0)
# 结算方式编码到ID映射
PM_ID_MAP = {
    "10": {"name":"转账","id":1223910},
    "11": {"name":"不付款","id":4159915},
    "JSFS01_SYS": {"name":"现金","id":1},
    "JSFS06_SYS": {"name":"商业承兑汇票","id":6},
    "JSFS07_SYS": {"name":"银行承兑汇票","id":7},
    "JSFS09_SYS": {"name":"应收票据背书","id":9}
}
# 应付票据的票据类型对应的结算方式，1：银行承兑汇票，2：商业承兑汇票
PAY_BILL_TYPE_PM_ID_MAP = {
    "1": "JSFS07_SYS", 
    "2": "JSFS06_SYS"
}


"""
等价于 Kingdee 的 FieldUtils.SetBaseDataFieldValue
ctx: 上下文，通过 this.Context 获取
bdField: BaseDataField 对象，字段的完整定义
entityData：实体数据包，即 bdField 这个字段所归属的实体数据包，类型在多数情况下都是：DynamicObject
newId：新的id，即这个实体对应的数据模型（如：结算方式、银行账户）

给单据数据包中的基础资料字段赋值（等价于 Kingdee 的 FieldUtils.SetBaseDataFieldValue）。
基础资料字段在数据包里由两个属性共同构成，必须同时赋值：
<PropertyName>_Id：引用内码（id），保存时写入外键列，决定落库结果；
<PropertyName>：引用数据包（DynamicObject），决定当前界面显示与引用属性取数。
只写内码，当前数据包里的引用对象仍是旧值（下推后界面空白或显示旧值，实体服务规则、保存校验按引用属性取数也会取错）；
只写引用包，保存时外键仍取旧id，落库还是旧值。
因此本函数先按传入的新id加载新的基础资料包，再把两个属性一起写。

1、ctx: 执行上下文。
2、fieldMeta: 字段元数据对象，类型：BaseDataField，即要更改哪个基础资料字段，就获取这个字段的 BaseDataField 对象然后传递过来
    获取方式：e.TargetBusinessInfo.GetField("FSETTLETYPEID") -> 获取 FSETTLETYPEID 的 BaseDataField 对象
    本函数会用到它的三个属性：
        RefFormDynamicObjectType：字段的引用类型，作为 LoadSingle 的类型参数，用它才能保证加载出来的数据包与字段的引用属性一致
        DynamicProperty：数据包里的引用对象属性，如：SETTLETYPEID
        RefIDDynamicProperty：数据包里的引用内码属性，如：SETTLETYPEID_Id

        字段在哪一层实体上，就要配合同一层的数据包使用（见 ownerObj）。
3、dataObj：字段所在的那条数据包，不是字段的值，也不是基础资料包
    字段为单据头字段，传单据头数据包，如：billHead = e.Result.FindByEntityKey("FBillHead")[i].DataEntity
    字段为单据体字段，传该行分录对象，如：billHead["PAYBILLENTRY"][i]
    字段为子单据体字段，传子单据体行对象，如：billHead["PAYBILLENTRY"][i]["子单据体key"][i]
4、newId，新值的内码（id），会通过这个id加载出对应的数据包
"""
def setBaseDataFieldValue(ctx, fieldMeta, dataObj, newId):
    # 转换为Int64，金蝶的id都是long类型的
    newLongId = Convert.ToInt64(newId)
    # 按id查一条记录，返回这条记录的数据实体（DynamicObject 数据包）
    # fieldMeta.RefFormDynamicObjectType 表示按什么类型装配数据包，比如当前的 bdField 是结算方式字段的字段元数据对象
    # 那么最终返回的 DynamicObject 数据包就是结算方式数据包
    newDO = BusinessDataServiceHelper.LoadSingle(ctx, newLongId, fieldMeta.RefFormDynamicObjectType)
    if newDO is None:
        return False
    # 用新的数据包替换老的
    fieldMeta.DynamicProperty.SetValue(dataObj, newDO)          # 引用数据包：界面显示
    if fieldMeta.RefIDDynamicProperty is not None:
        # 用新的id，替换老的数据包里面的id字段，如 SETTLETYPEID_Id
        fieldMeta.RefIDDynamicProperty.SetValue(dataObj, newId)    # 引用内码：落库、列表取数
    else:
        dataObj[fieldMeta.PropertyName + "_Id"] = newId
    return True


# 获取类型
def getType(obj):
    raise Exception("类型：" + toStr(type(obj)))


# 安全获取字典key值
def mapGet(m, key):
    if not m:
        return None
    try:
        return m[key]
    except Exception:
        return None


# 异常打印
def eprint(s):
    if s is None:
        return
    raise Exception(toStr(s))


# 获取对象的属性和方法
def getKeys(obj):
    keys = dir(obj)
    raise Exception("; ".join(keys))


# 序列化对象为json字符串
def toJsonStr(data):
    if data is None:
        eprint("")
    s = JsonConvert.SerializeObject(data)
    eprint(s)


def toStr(s):
    if s is None:
        return "None"
    if isinstance(s, basestring):
        return s
    return str(s)


def _propType(prop, value):
    """优先用实际值的运行时类型；值为空时退回元数据里的字段类型"""
    if value is not None:
        try:
            t = value.GetType()
            if t is not None:
                return str(t.Name)          # String / Int64 / Decimal / DateTime / DynamicObject
        except Exception:
            pass
    try:
        t = prop.PropertyType
        if t is not None:
            name = getattr(t, "Name", None)
            return str(name) if name else str(t)
    except Exception:
        pass
    return "None"


def dumpDoFields(do):
    """DynamicObject -> <field:xx,type:xx>;<field:xx,type:xx>;..."""
    if do is None:
        return ""
    try:
        props = do.DynamicObjectType.Properties
    except Exception:
        return ""

    parts = []
    for prop in props:
        name = str(prop.Name)               # 必须 str()，否则会报 __getitem__ 重载歧义
        value = None
        try:
            value = do[name]
        except Exception:
            pass
        parts.append("<field:{0},type:{1}>".format(name, _propType(prop, value)))
    return ";".join(parts)


# =================================================================================
# ====================================  begin  ====================================
# =================================================================================


# 是否有汇票类别的结算方式
HAS_DRAFT_PM = False


# 分录参数校验
def checkReqDetailParams(reqDetails, billNumbers, baMap):
    global HAS_DRAFT_PM
    error = ""
    for i in range(reqDetails.Count):
        prefix = ("" if i == 0 else "; ") + "第%d条分录参数校验失败：" % (i + 1)
        reqDetail = reqDetails[i]
        
        # 校验结算方式
        pm = reqDetail.Get("PaymentMethod")
        if not pm:
            error += prefix + "缺少结算方式"
            continue
        if pm not in VALID_PM:
            error += prefix + "无效的结算方式"
            continue

        # 校验实付金额
        amount = reqDetail.Get("ActualPaymentAmount")
        if amount is None or toStr(amount).strip() == "":
            error += prefix + "缺少实付金额"
            continue
        try:
            amount = Decimal.Parse(toStr(amount)) # 解析金额字符串
        except FormatException:
            error += prefix + "无效的实付金额"
            continue
        if amount < ZERO:
            error += prefix + "实付金额不能为负数"
            continue
        reqDetail.Put("DecimalActualPaymentAmount", amount)

        # 结算方式 10 需要银行账号
        if pm == VALID_PM[0]:
            ba = reqDetail.Get("BankAccount")
            if not ba:
                error += prefix + "当前结算方式（编码：%s）的业务分类为银行业务，需要录入银行账号" % pm
                continue
            baMap[ba] = -1
        # 票据类结算方式需要票据流水号
        if pm in NEED_BILL_PM:
            if not billNumbers:
                error += prefix + "当前结算方式（编码：%s）的业务分类为票据业务，需要录入票据流水号" % pm
                continue
            HAS_DRAFT_PM = True
    
    if error:
        raise Exception(error)


# 通过银行账号获取对应的id，并填充
def fullBankAccountId(ctx, baMap):
    accounts = ""
    for k in baMap:
        ba = toStr(k).strip().replace("'", "''") # 银行账号，简单转义，防引号截断
        prefix = "," if accounts else ""
        accounts += "{0}'{1}'".format(prefix, ba)
    sql = "/*dialect*/ SELECT FBANKACNTID, FNUMBER FROM T_CN_BANKACNT WHERE FNUMBER IN ({0})".format(accounts)
    # 执行sql，若无查询结果集，不会返回None，而是空集合Count = 0
    rows = DBServiceHelper.ExecuteDynamicObject(ctx, sql)
    for row in rows:
      # 编码映射id
        baMap[toStr(row["FNUMBER"])] = Convert.ToInt64(row["FBANKACNTID"])


# 通过票据流水号查询应付票据实体
def getPayBillByFlowNumber(ctx, flowNumbers):
    res = {}
    numbers = ""
    for fn in flowNumbers:
        fn = toStr(fn).strip().replace("'", "''") # 票据流水号账号，简单转义，防引号截断
        prefix = "," if numbers else ""
        numbers += "{0}'{1}'".format(prefix, fn)
    sql = "/*dialect*/ SELECT * FROM V_CN_BILLPAYABLE WHERE FNUMBER IN ({0})".format(numbers)
    # 执行sql，若无查询结果集，不会返回None，而是空集合Count = 0
    rows = DBServiceHelper.ExecuteDynamicObject(ctx, sql)
    for row in rows:
      # 编码映射应付票据实体
        res[toStr(row["FNUMBER"])] = row
    return res


# 后置节点钩子函数
def AfterConvert(e):
    # 读取请求参数中的 CustomParams 参数，返回值类型是字典
    customParams = this.Option.GetVariables()
    
    # Detail字段对应单据分录数组，如果没有Detail字段，视为前台下推，走标准下推流程
    reqDetails = mapGet(customParams, "Detail")
    if not reqDetails:
        return

    # 获取票据流水号列表
    billNumbers = mapGet(customParams, "BillDetail") 
    
    # 收集银行账号
    baMap = {}

    # 校验分录参数
    checkReqDetailParams(reqDetails, billNumbers, baMap) 
    
    # 获取下游付款单单据头集合，类型：DynamicObjectCollection
    billHeads = e.Result.FindByEntityKey("FBillHead") 
    if not billHeads:
        return
    
    # 有银行账户，则获取其id并填充baMap
    if baMap:
        fullBankAccountId(this.Context, baMap)

    # 取出“结算方式”这个字段的完整定义（字段元数据对象），类型：BaseDataField，注意，通过字段标识获取而不是实体属性
    pmFieldMeta = e.TargetBusinessInfo.GetField("FSETTLETYPEID")  # FSETTLETYPEID 是分录实体下的字段
    # 同理取出“我方银行账号”这个字段的完整定义（字段元数据对象）
    baFieldMeta = e.TargetBusinessInfo.GetField("FACCOUNTID")  # FACCOUNTID 是分录实体下的字段

    for billHeadObj in billHeads:
        # 下游付款单单据头  DynamicObject
        billHead = billHeadObj.DataEntity
        # 付款单分录明细列表 类型：DynamicObjectCollection
        billDetails = mapGet(billHead, "PAYBILLENTRY")    
        if not billDetails:
            continue
        
        for i in range(billDetails.Count):
            billDetail = billDetails[i]    # 单据分录明细实体，类型：DynamicObject
            reqDetail = reqDetails[i] # 请求传递的分录
            
            # getType(detail["SETTLETYPEID"])
            # getJSONObjectMethodAndAttribute(detail)
            # s = "id: " + str(detail["SETTLETYPEID"]["Id"]) + ", number: " + detail["SETTLETYPEID"]["Number"]
            # eprint(s)
            
            # 更新结算方式
            pmObj = mapGet(billDetail, "SETTLETYPEID") # 从分录实体中获取结算方式，结算方式是基础资料，类型：DynamicObject
            pmCode = reqDetail.Get("PaymentMethod") # 请求分录中的结算方式编码
            pmCodeId = PM_ID_MAP[pmCode]["id"] # 结算方式编码的id
            # 调用方法用新的结算方式id更新当前分录中的结算方式数据包，当前pmFieldMeta指向的是结算方式字段，所属对象是billDetail
            # 所以要传billDetail
            setBaseDataFieldValue(this.Context, pmFieldMeta, billDetail, pmCodeId)
            
            # 更新实付金额
            amt = reqDetail.Get("DecimalActualPaymentAmount")
            billDetail["REALPAYAMOUNTFOR"] = amt # REALPAYAMOUNTFOR_D：实付金额（原币）
            billDetail["REALPAYAMOUNT"] = amt # REALPAYAMOUNT_D：实付金额（本位币）
            
            # 更新银行账号
            account = reqDetail.Get("BankAccount")
            if pmCode == VALID_PM[0] and account:
                baId = mapGet(baMap, account)
                if baId is None or baId == -1:
                    raise Exception("银行账号（{0}）无效，无法获取账号 ID".format(account))
                # 我方银行账号这个字段属于基础资料（DynamicObject），用setBaseDataFieldValue()更新
                setBaseDataFieldValue(this.Context, baFieldMeta, billDetail, baId)
        
        # 处理应付票据
        if HAS_DRAFT_PM:
            # 取出“票据流水号”这个字段的完整定义（字段元数据对象）
            bFieldMeta = e.TargetBusinessInfo.GetField("FBILLID")
        
            # 应付票据列表，类型：DynamicObjectCollection
            payBillList = mapGet(billHead, "PAYBILLPAYABLE")
            payBill = payBillList[0] # 应付票据分录实体，DynamicObject
            billNumber = billNumbers[0] # 请求传递的票据流水号
            # 通过票据流水号列表查询应付票据实体
            res = getPayBillByFlowNumber(this.Context, billNumbers)
            pbId = res[billNumber]["fbillid"] # 应付票据id
            # 更新应付票据分录实体下的票据流水号
            setBaseDataFieldValue(this.Context, bFieldMeta, payBill, pbId)