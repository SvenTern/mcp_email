// Bitrix24 REST API Types
export var TaskPriority;
(function (TaskPriority) {
    TaskPriority[TaskPriority["LOW"] = 0] = "LOW";
    TaskPriority[TaskPriority["NORMAL"] = 1] = "NORMAL";
    TaskPriority[TaskPriority["HIGH"] = 2] = "HIGH";
})(TaskPriority || (TaskPriority = {}));
export var TaskStatus;
(function (TaskStatus) {
    TaskStatus[TaskStatus["NEW"] = 1] = "NEW";
    TaskStatus[TaskStatus["PENDING"] = 2] = "PENDING";
    TaskStatus[TaskStatus["IN_PROGRESS"] = 3] = "IN_PROGRESS";
    TaskStatus[TaskStatus["SUPPOSEDLY_COMPLETED"] = 4] = "SUPPOSEDLY_COMPLETED";
    TaskStatus[TaskStatus["COMPLETED"] = 5] = "COMPLETED";
    TaskStatus[TaskStatus["DEFERRED"] = 6] = "DEFERRED";
})(TaskStatus || (TaskStatus = {}));
export var TaskMark;
(function (TaskMark) {
    TaskMark["NEGATIVE"] = "N";
    TaskMark["POSITIVE"] = "P";
})(TaskMark || (TaskMark = {}));
//# sourceMappingURL=bitrix.js.map