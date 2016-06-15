#!/usr/bin/env python
# coding:utf-8

from toughlib import utils
from toughlib import logger
from toughradius.manage import models
from toughlib.dbutils import make_db
from toughradius.manage.settings import PPTimes, PPFlow
from toughradius.manage.tasks.task_base import TaseBasic
from toughradius.manage import taskd
from toughradius.common.event_common import trigger_notify


class InsufficientBalanceNotifyTask(TaseBasic):

    __name__ = 'insufficient_balance_notify'

    def get_notify_interval(self):
        try:
            notify_interval = int(self.get_param_value("mail_notify_interval",1440)) * 60.0
            notify_time = self.get_param_value("mail_notify_time", None)
            if notify_time:
                notify_interval = utils.get_cron_interval(notify_time)
            return notify_interval
        except:
            return 120

    def first_delay(self):
        return self.get_notify_interval()

    def process(self, *args, **kwargs):
        self.logtimes()
        next_interval = self.get_notify_interval()
        try:
            logger.info("start process insufficient balance notify task")

            with make_db(self.db) as db:
                expire_query = db.query(
                    models.TrCustomer.mobile,
                    models.TrCustomer.realname,
                    models.TrCustomer.email,
                    models.TrProduct.product_name,
                    models.TrAccount.balance,
                    models.TrAccount.account_number,
                ).filter(
                    models.TrCustomer.customer_id == models.TrAccount.customer_id,
                    models.TrAccount.product_id == models.TrProduct.id,
                    models.TrProduct.product_policy.in_((PPTimes, PPFlow)),
                    models.TrAccount.status == 1
                )

                notifys = dict(toughcloud_sms='toughcloud_sms_account_insufficient_balance')
                notifys['smtp_mail'] = 'smtp_account_insufficient_balance'
                notifys['toughcloud_mail'] = 'toughcloud_mail_account_insufficient_balance'

                for user_info in expire_query:
                    trigger_notify(self, user_info, **notifys)

                logger.info(u"余额不足通知任务已执行(%s个已通知)。下次执行还需等待 %s" % (
                    expire_query.count(), self.format_time(next_interval)), trace="task")
                
        except Exception as err:
            logger.info(u"余额不足通知任务执行失败，%s。下次执行还需等待 %s" % (
                        repr(err), self.format_time(next_interval)), trace="task")
            logger.exception(err)

        return next_interval

taskd.TaskDaemon.__taskclss__.append(InsufficientBalanceNotifyTask)