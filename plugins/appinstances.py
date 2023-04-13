import argparse
import droveclient
import droveutils
import json
import plugins

from operator import itemgetter
from types import SimpleNamespace

class Applications(plugins.DrovePlugin):
    def __init__(self) -> None:
        pass

    def populate_options(self, drove_client: droveclient.DroveClient, subparser: argparse.ArgumentParser):
        parser = subparser.add_parser("appinstances", help="Drove application instance related commands")

        commands = parser.add_subparsers(help="Available commands for application management")

        sub_parser = commands.add_parser("list", help="List all application instances")
        sub_parser.add_argument("app_id", metavar="app-id", help="Application ID")
        sub_parser.add_argument("--old", "-o", help="Show old instances", action="store_true")
        sub_parser.add_argument("--sort", "-s", help="Sort output by column", type=int, choices=range(0, 6), default = 0)
        sub_parser.add_argument("--reverse", "-r", help="Sort in reverse order", action="store_true")
        sub_parser.set_defaults(func=self.list_instances)

        sub_parser = commands.add_parser("info", help="Print details for an application instance")
        sub_parser.add_argument("app_id", metavar="app-id", help="Application ID")
        sub_parser.add_argument("instance_id", metavar="instance-id", help="Application Instance ID")
        sub_parser.set_defaults(func=self.show_instance)

        sub_parser = commands.add_parser("logs", help="Print list of logs for application instance")
        sub_parser.add_argument("app_id", metavar="app-id", help="Application ID")
        sub_parser.add_argument("instance_id", metavar="instance-id", help="Application Instance ID")
        sub_parser.set_defaults(func=self.show_logs_list)

        sub_parser = commands.add_parser("tail", help="Tail log for application instance")
        sub_parser.add_argument("app_id", metavar="app-id", help="Application ID")
        sub_parser.add_argument("instance_id", metavar="instance-id", help="Application Instance ID")
        sub_parser.add_argument("--file", "-f", default = "output.log", help="Log filename to tail. Default is to tail output.log")
        sub_parser.set_defaults(func=self.log_tail)

        sub_parser = commands.add_parser("download", help="Download log for application instance")
        sub_parser.add_argument("app_id", metavar="app-id", help="Application ID")
        sub_parser.add_argument("instance_id", metavar="instance-id", help="Application Instance ID")
        sub_parser.add_argument("file", help="Log filename to download")
        sub_parser.add_argument("--out", "-o", help="Filename to download to. Default is the same filename as provided.")

        sub_parser.set_defaults(func=self.log_download)

        # sub_parser = commands.add_parser("create", help="Create application")
        # sub_parser.add_argument("definition", help="JSON application definition")
        
        super().populate_options(drove_client, parser)


    def list_instances(self, options: SimpleNamespace):
        api = "/apis/v1/applications/{app_id}/instances"
        if options.old:
            api = "/apis/v1/applications/{app_id}/instances/old"
        data = self.drove_client.get(api.format(app_id = options.app_id))
        #headers = ["Instance ID", "Executor", "CPU", "Memory(MB)", "State", "Error Message", "Created", "Last Updated"]
        headers = ["Instance ID", "Executor Host", "State", "Error Message", "Created", "Last Updated"]
        rows = []
        for instance in data:
            instance_row = []
            instance_row.append(instance["instanceId"])
            try:
                instance_row.append(instance["localInfo"]["hostname"])
            except KeyError:
                instance_row.append("")
            instance_row.append(instance["state"])
            instance_row.append(instance["errorMessage"])
            instance_row.append(droveutils.to_date(instance["created"]))
            instance_row.append(droveutils.to_date(instance["updated"]))

            rows.append(instance_row)
        rows = sorted(rows, key=itemgetter(options.sort), reverse=options.reverse)
        droveutils.print_table(headers, rows)

    def show_instance(self, options):
        raw = self.drove_client.get("/apis/v1/applications/{app_id}/instances/{instance_id}".format(app_id = options.app_id, instance_id=options.instance_id))
        data = dict()
        data["Instance ID"] = raw["instanceId"]
        data["App ID"] = raw["appId"]
        data["State"] = raw["state"]
        data["Host"] = raw.get("localInfo", dict()).get("hostname", "")
        cpu_list = [r for r in raw.get("resources", list()) if r.get("type", "") == "CPU"]
        if len(cpu_list) > 0:
            data["CPU"] = ", ".join(["NUMA Node %s: Cores: %s" % (key, value) for (key, value) in cpu_list[0].get("cores", dict()).items()])
        memory_list = [r for r in raw.get("resources", list()) if r.get("type", "") == "MEMORY"]
        if len(memory_list) > 0:
            data["Memory (MB)"] = ", ".join(["NUMA Node %s: Cores: %s" % (key, value) for (key, value) in memory_list[0].get("memoryInMB", dict()).items()])
        ports = raw.get("localInfo", dict()).get("ports", dict())
        data["Ports"] = ", ".join(["Name: %s %s" % (key, "Container: {container} Host: {host} Type: {type}".format(container = value.get("containerPort", ""), host = value.get("hostPort", ""), type = value.get("portType", ""))) for (key, value) in ports.items()])
        data["Metadata"] = ", ".join(["%s: %s" % (key,value) for (key, value) in raw.get("metadata", dict())])
        data["Error Message"] = raw.get("errorMessage", "").strip('\n')
        data["Created"] = droveutils.to_date(raw.get("created"))
        data["Last Updated"] = droveutils.to_date(raw.get("updated"))

        droveutils.print_dict(data)

    def show_logs_list(self, options):
        droveutils.list_logs(self.drove_client, "applications", options.app_id, options.instance_id)

    def log_tail(self, options):
        droveutils.tail_log(self.drove_client, "applications", options.app_id, options.instance_id, options.file)
        
    def log_download(self, options):
        filename = options.file
        if options.out and len(options.out) > 0:
            filename = options.out
        droveutils.download_log(self.drove_client, "applications", options.app_id, options.instance_id, options.file, filename)
