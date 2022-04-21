from inspect import getdoc, signature
from typing import Any, Callable, Coroutine, Dict, List, Optional, Union

from interactions import MISSING, Client, Guild, InteractionException, Option, OptionType

from ._logging import get_logger
from .command_models import parameters_to_options

log = get_logger("subcommand")


class SubcommandManager:
    def __init__(self, manager: "Manager") -> None:
        self.m = manager

    def __call__(
        self,
        _coro: Optional[Coroutine] = MISSING,
        *,
        name: Optional[str] = MISSING,
        description: Optional[str] = MISSING,
        options: Optional[List[Option]] = MISSING,
    ) -> Callable[..., Any]:
        def decorator(coro: Coroutine) -> Coroutine:
            _name = coro.__name__ if name is MISSING else name
            _description = (
                (getdoc(coro) or "No description") if description is MISSING else description
            ).split("\n")[0]
            if len(_description) > 100:
                raise ValueError("Description must be less than 100 characters.")

            params = signature(coro).parameters
            _options = (
                getattr(coro, "__decor_options")
                if hasattr(coro, "__decor_options")
                else parameters_to_options(params[1:])
                if options is MISSING and len(params) > 2
                else None
                if options is MISSING
                else options
            )

            if not params:
                raise InteractionException(
                    11,
                    message="Your command needs at least one argument to return context.",
                )

            self.m.data.append(
                Option(
                    type=OptionType.SUB_COMMAND,
                    name=_name,
                    description=_description,
                    options=_options,
                )._json
            )
            self.m.coroutines[_name] = coro
            self.m.sync_client_commands()

            return coro

        if _coro is not MISSING:
            return decorator(_coro)
        return decorator


class GroupManager:
    def __init__(self, manager: "Manager") -> None:
        self.m = manager
        self.group: Optional[str] = None

    def __call__(
        self,
        _coro: Optional[Coroutine] = MISSING,
        *,
        group: Optional[str] = MISSING,
    ) -> Callable[..., Any]:
        def decorator(coro: Coroutine) -> Coroutine:
            _group = coro.__name__ if group is MISSING else group
            self.m.data.append(
                Option(
                    type=OptionType.SUB_COMMAND_GROUP,
                    name=_group,
                    description=(getdoc(coro) or "No description").split("\n")[0],
                )._json
            )
            self.m.groups.append(_group)
            self.m.coroutines[_group] = coro
            self.group = _group

            try:
                coro.subcommand = self.subcommand
            except AttributeError:
                coro.__func__.subcommand = self.subcommand

            self.m.sync_client_commands()

            return coro

        if _coro is not MISSING:
            return decorator(_coro)
        return decorator

    def subcommand(
        self,
        _coro: Optional[Coroutine] = MISSING,
        *,
        name: Optional[str] = MISSING,
        description: Optional[str] = MISSING,
        options: Optional[List[Option]] = MISSING,
    ) -> Callable[..., Any]:
        def decorator(coro: Coroutine) -> Coroutine:
            _name = coro.__name__ if name is MISSING else name
            _description = (
                (getdoc(coro) or "No description") if description is MISSING else description
            ).split("\n")[0]
            if len(_description) > 100:
                raise ValueError("Description must be less than 100 characters.")

            params = signature(coro).parameters
            _options = (
                getattr(coro, "__decor_options")
                if hasattr(coro, "__decor_options")
                else parameters_to_options(params[1:])
                if options is MISSING and len(params) > 2
                else None
                if options is MISSING
                else options
            )

            if not params:
                raise InteractionException(
                    11,
                    message="Your command needs at least one argument to return context.",
                )

            if not self.group:
                raise InteractionException(
                    12,
                    message="You must call `group` before calling `subcommand`.",
                )

            for i, group in enumerate(self.m.data):
                if group["type"] == OptionType.SUB_COMMAND_GROUP and group["name"] == self.group:
                    if group.get("options"):
                        self.m.data[i]["options"].append(
                            Option(
                                type=OptionType.SUB_COMMAND,
                                name=_name,
                                description=_description,
                                options=_options,
                            )._json
                        )
                    else:
                        self.m.data[i]["options"] = [
                            Option(
                                type=OptionType.SUB_COMMAND,
                                name=_name,
                                description=_description,
                                options=_options,
                            )._json
                        ]
                    break

            self.m.coroutines[f"{self.group} {_name}"] = coro

            self.m.sync_client_commands()

            return coro

        if _coro is not MISSING:
            return decorator(_coro)
        return decorator


class Manager:
    def __init__(
        self,
        coro: Coroutine,
        base: str,
        description: str,
        scope: Union[int, Guild, List[int], List[Guild]],
        default_permission: bool,
        client: Optional[Client] = None,
    ) -> None:
        self.base = base
        self.description = description
        self.scope = scope
        self.default_permission = default_permission
        self.client = client

        self.groups: List[str] = []
        self.data: List[dict] = []
        self.base_coroutine: Coroutine = coro
        self.coroutines: Dict[str, Coroutine] = {}

        self.subcommand = SubcommandManager(self)
        self.group = GroupManager(self)

        if self.client and not hasattr(self.client, "_command_data"):
            self.client._command_data = []

    @property
    def full_data(self):
        return {
            "name": self.base,
            "type": 1,
            "description": self.description,
            "options": self.data,
        }

    def sync_client_commands(self):
        if not self.client:
            return

        if not self.client._command_data:
            self.client._command_data = [self.full_data]
        elif any(cmd["name"] == self.base for cmd in self.client._command_data):
            for i, cmd in enumerate(self.client._command_data):
                if cmd["name"] == self.base:
                    self.client._command_data[i] = self.full_data
        else:
            self.client._command_data.append(self.full_data)

        if not hasattr(self.client, "_command_coros") or not self.client._command_coros:
            self.client._command_coros = {self.base: self.subcommand_caller}
        else:
            self.client._command_coros[self.base] = self.subcommand_caller

    async def subcommand_caller(
        self,
        ctx,
        *args,
        sub_command_group: Optional[str] = None,
        sub_command: Optional[str] = None,
        **kwargs,
    ):
        base_coro = self.base_coroutine
        base_res = await base_coro(ctx, *args, **kwargs)
        if sub_command_group:
            group_coro = self.coroutines[sub_command_group]
            subcommand_coro = self.coroutines[f"{sub_command_group} {sub_command}"]
            group_res = await group_coro(ctx, base_res, *args, **kwargs)
            return await subcommand_coro(ctx, group_res, *args, **kwargs)
        else:
            subcommand_coro = self.coroutines[sub_command]
            return await subcommand_coro(ctx, base_res, *args, **kwargs)