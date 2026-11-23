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


"""DynamicObject -> <field:xx,type:xx>;<field:xx,type:xx>;..."""
def dumpDoFields(do):
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