"""Config and options flow for Somfy HA Gateway V3."""

from __future__ import annotations

import json
import re
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import selector

from .const import (
    CONF_ADDRESS,
    CONF_COVER_ID,
    CONF_COVER_NAME,
    CONF_COVER_TYPE,
    CONF_COVERS,
    CONF_COVERS_JSON,
    CONF_MY_POSITION,
    CONF_NAME,
    CONF_OBSERVED_ADDRESSES,
    CONF_POSITION,
    CONF_REPEAT,
    CONF_ROLLING,
    CONF_RX_ENTITY,
    CONF_TIME_IN,
    CONF_TIME_OUT,
    CONF_TX_ENTITY,
    DEFAULT_RX_ENTITY,
    DEFAULT_TX_ENTITY,
    DOMAIN,
)
from .models import normalize_cover_config

COVER_TYPES = ["blind", "awning", "curtain", "shutter"]
ADDRESS_PATTERN = re.compile(r"^[0-9A-Fa-f]{1,6}$")


def normalize_covers(value: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Normalize and validate a list of cover configuration dictionaries."""
    if not isinstance(value, list):
        raise ValueError("covers must be a list")

    normalized: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for item in value:
        if not isinstance(item, dict):
            raise ValueError("each cover must be an object")

        cover = normalize_cover_config(item)
        _validate_address(cover[CONF_ADDRESS])

        cover_id = cover[CONF_COVER_ID]
        if cover_id in seen_ids:
            raise ValueError(f"duplicate cover id: {cover_id}")

        seen_ids.add(cover_id)
        normalized.append(cover)

    return normalized


def normalize_covers_json(covers_json: str) -> list[dict[str, Any]]:
    """Normalize a JSON text field containing cover definitions."""
    covers = json.loads(covers_json)
    if not isinstance(covers, list):
        raise ValueError("covers must be a list")
    return normalize_covers(covers)


def _validate_address(value: str) -> str:
    """Validate and normalize a Somfy RTS address."""
    address = str(value).strip().upper()
    if not ADDRESS_PATTERN.match(address):
        raise ValueError("address must be 1-6 hex characters")
    return address.zfill(6)


def _validate_observed_addresses(value: str | list[str]) -> list[str]:
    """Validate optional comma-separated observed addresses."""
    if isinstance(value, str):
        parts = [part.strip() for part in value.split(",") if part.strip()]
    else:
        parts = [str(part).strip() for part in value if str(part).strip()]
    return [_validate_address(part) for part in parts]


def _cover_form_schema(
    defaults: dict[str, Any] | None = None,
    *,
    include_id: bool = True,
) -> vol.Schema:
    """Return the add/edit cover form schema."""
    defaults = defaults or {}
    fields: dict[Any, Any] = {}

    if include_id:
        fields[
            vol.Required(
                CONF_COVER_ID,
                default=defaults.get(CONF_COVER_ID, ""),
            )
        ] = selector.TextSelector()

    fields.update(
        {
            vol.Required(
                CONF_COVER_NAME,
                default=defaults.get(CONF_COVER_NAME, ""),
            ): selector.TextSelector(),
            vol.Required(
                CONF_ADDRESS,
                default=defaults.get(CONF_ADDRESS, ""),
            ): selector.TextSelector(),
            vol.Required(
                CONF_ROLLING,
                default=defaults.get(CONF_ROLLING, 1),
            ): vol.All(vol.Coerce(int), vol.Range(min=1, max=65535)),
            vol.Required(
                CONF_REPEAT,
                default=defaults.get(CONF_REPEAT, 2),
            ): vol.All(vol.Coerce(int), vol.Range(min=0, max=20)),
            vol.Optional(
                CONF_OBSERVED_ADDRESSES,
                default=",".join(defaults.get(CONF_OBSERVED_ADDRESSES, [])),
            ): selector.TextSelector(),
            vol.Required(
                CONF_POSITION,
                default=defaults.get(CONF_POSITION, 0),
            ): vol.All(vol.Coerce(int), vol.Range(min=0, max=100)),
            vol.Required(
                CONF_COVER_TYPE,
                default=defaults.get(CONF_COVER_TYPE, "blind"),
            ): vol.In(COVER_TYPES),
            vol.Required(
                CONF_TIME_OUT,
                default=defaults.get(CONF_TIME_OUT, 30),
            ): vol.All(vol.Coerce(int), vol.Range(min=1, max=300)),
            vol.Required(
                CONF_TIME_IN,
                default=defaults.get(CONF_TIME_IN, 30),
            ): vol.All(vol.Coerce(int), vol.Range(min=1, max=300)),
            vol.Required(
                CONF_MY_POSITION,
                default=defaults.get(CONF_MY_POSITION, 50),
            ): vol.All(vol.Coerce(int), vol.Range(min=0, max=100)),
        }
    )

    return vol.Schema(fields)


def _slugify_cover_id(value: str) -> str:
    """Convert a user supplied name into a stable cover id."""
    slug = re.sub(r"[^a-zA-Z0-9_]+", "_", value.strip().lower()).strip("_")
    if not slug:
        raise ValueError("cover name is required")
    return slug


def _unique_cover_id(base_id: str, covers: list[dict[str, Any]]) -> str:
    """Return a unique cover id by appending a numeric suffix if needed."""
    existing_ids = {cover[CONF_COVER_ID] for cover in covers}

    if base_id not in existing_ids:
        return base_id

    index = 2
    while f"{base_id}_{index}" in existing_ids:
        index += 1

    return f"{base_id}_{index}"


class SomfyConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the initial setup flow."""

    VERSION = 1

    @staticmethod
    def async_get_options_flow(config_entry):
        """Return the options flow."""
        return SomfyOptionsFlowHandler(config_entry)

    async def async_step_user(self, user_input=None):
        """Create the gateway entry.

        Covers are intentionally not created here. They are managed from the
        options flow so users do not need to edit raw JSON.
        """
        errors = {}

        if user_input is not None:
            data = {
                CONF_NAME: user_input[CONF_NAME],
                CONF_TX_ENTITY: user_input[CONF_TX_ENTITY],
                CONF_RX_ENTITY: user_input.get(CONF_RX_ENTITY, ""),
                CONF_COVERS: [],
            }

            return self.async_create_entry(
                title=data[CONF_NAME],
                data=data,
            )

        schema = vol.Schema(
            {
                vol.Required(CONF_NAME, default="Somfy HA Gateway V3"): str,
                vol.Required(
                    CONF_TX_ENTITY,
                    default=DEFAULT_TX_ENTITY,
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="text")
                ),
                vol.Optional(
                    CONF_RX_ENTITY,
                    default=DEFAULT_RX_ENTITY,
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )


class SomfyOptionsFlowHandler(config_entries.OptionsFlow):
    """Options flow with UI CRUD for covers."""

    def __init__(self, config_entry):
        self._config_entry = config_entry
        self._selected_cover_id: str | None = None

    def _current_data(self) -> dict[str, Any]:
        """Return merged immutable data and mutable options."""
        current_data = dict(self._config_entry.data)
        current_options = dict(self._config_entry.options)
        return {**current_data, **current_options}

    def _current_covers(self) -> list[dict[str, Any]]:
        """Return normalized current covers."""
        current = self._current_data()
        return normalize_covers(current.get(CONF_COVERS, []))

    def _base_options(self, covers: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        """Build a complete options dictionary."""
        current = self._current_data()
        return {
            CONF_NAME: current.get(CONF_NAME, "Somfy HA Gateway V3"),
            CONF_TX_ENTITY: current.get(CONF_TX_ENTITY, DEFAULT_TX_ENTITY),
            CONF_RX_ENTITY: current.get(CONF_RX_ENTITY, DEFAULT_RX_ENTITY),
            CONF_COVERS: covers if covers is not None else self._current_covers(),
        }

    def _cover_options(self) -> dict[str, str]:
        """Return cover select options mapping id -> label."""
        covers = self._current_covers()
        return {
            cover[CONF_COVER_ID]: f"{cover[CONF_COVER_NAME]} ({cover[CONF_COVER_ID]})"
            for cover in covers
        }

    def _get_selected_cover(self) -> dict[str, Any] | None:
        """Return the cover selected in a previous menu step."""
        if not self._selected_cover_id:
            return None

        for cover in self._current_covers():
            if cover[CONF_COVER_ID] == self._selected_cover_id:
                return cover

        return None

    def _remove_cover_entities_from_registry(self, cover_id: str) -> None:
        """Remove entity registry entries for a deleted cover."""
        entity_registry = er.async_get(self.hass)
        entry_id = self._config_entry.entry_id

        unique_ids_by_domain = {
            "cover": [
                f"{entry_id}_{cover_id}_cover",
            ],
            "text": [
                f"{entry_id}_{cover_id}_address",
                f"{entry_id}_{cover_id}_observed_addresses",
            ],
            "number": [
                f"{entry_id}_{cover_id}_position",
                f"{entry_id}_{cover_id}_rolling",
                f"{entry_id}_{cover_id}_repeat",
                f"{entry_id}_{cover_id}_time_out",
                f"{entry_id}_{cover_id}_time_in",
                f"{entry_id}_{cover_id}_my_position",
            ],
            "select": [
                f"{entry_id}_{cover_id}_cover_type",
            ],
            "button": [
                f"{entry_id}_{cover_id}_prog",
            ],
        }

        for platform_domain, unique_ids in unique_ids_by_domain.items():
            for unique_id in unique_ids:
                entity_id = entity_registry.async_get_entity_id(
                    platform_domain,
                    DOMAIN,
                    unique_id,
                )
                if entity_id:
                    entity_registry.async_remove(entity_id)

    def _remove_cover_device_from_registry(self, cover_id: str) -> None:
        """Remove the device registry entry for a deleted cover."""
        device_registry = dr.async_get(self.hass)
        entry_id = self._config_entry.entry_id

        device = device_registry.async_get_device(
            identifiers={(DOMAIN, f"{entry_id}_{cover_id}")},
        )
        if device:
            device_registry.async_remove_device(device.id)

    def _remove_cover_from_registries(self, cover_id: str) -> None:
        """Remove both stale entities and the empty cover device."""
        self._remove_cover_entities_from_registry(cover_id)
        self._remove_cover_device_from_registry(cover_id)

    def _normalize_form_cover(
        self,
        user_input: dict[str, Any],
        *,
        existing_id: str | None = None,
        existing_covers: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Normalize one cover from add/edit form data."""
        cover = dict(user_input)

        if existing_id is not None:
            cover[CONF_COVER_ID] = existing_id
        else:
            base_id = _slugify_cover_id(str(cover[CONF_COVER_NAME]))
            cover[CONF_COVER_ID] = _unique_cover_id(base_id, existing_covers or [])

        cover[CONF_ADDRESS] = _validate_address(cover[CONF_ADDRESS])
        cover[CONF_OBSERVED_ADDRESSES] = _validate_observed_addresses(
            cover.get(CONF_OBSERVED_ADDRESSES, "")
        )

        return normalize_cover_config(cover)

    async def async_step_init(self, user_input=None):
        """Show the main options menu."""
        menu_options = {
            "gateway_settings": "Gateway settings",
            "add_cover": "Add cover",
        }

        if self._current_covers():
            menu_options["pick_remove_cover"] = "Remove cover"

        return self.async_show_menu(
            step_id="init",
            menu_options=menu_options,
        )

    async def async_step_gateway_settings(self, user_input=None):
        """Edit gateway-level settings."""
        errors = {}
        current = self._current_data()

        if user_input is not None:
            options = self._base_options()
            options[CONF_NAME] = user_input[CONF_NAME]
            options[CONF_TX_ENTITY] = user_input[CONF_TX_ENTITY]
            options[CONF_RX_ENTITY] = user_input.get(CONF_RX_ENTITY, "")
            return self.async_create_entry(title="", data=options)

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_NAME,
                    default=current.get(CONF_NAME, "Somfy HA Gateway V3"),
                ): str,
                vol.Required(
                    CONF_TX_ENTITY,
                    default=current.get(CONF_TX_ENTITY, DEFAULT_TX_ENTITY),
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="text")
                ),
                vol.Optional(
                    CONF_RX_ENTITY,
                    default=current.get(CONF_RX_ENTITY, DEFAULT_RX_ENTITY),
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),
            }
        )

        return self.async_show_form(
            step_id="gateway_settings",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_add_cover(self, user_input=None):
        """Add a new cover without editing raw JSON."""
        errors = {}

        if user_input is not None:
            try:
                covers = self._current_covers()
                new_cover = self._normalize_form_cover(
                    user_input,
                    existing_covers=covers,
                )
                covers.append(new_cover)

                return self.async_create_entry(
                    title="",
                    data=self._base_options(covers),
                )
            except ValueError:
                errors["base"] = "invalid_cover"
            except Exception:
                errors["base"] = "invalid_cover"

        return self.async_show_form(
            step_id="add_cover",
            data_schema=_cover_form_schema(
                {
                    CONF_COVER_NAME: "New cover",
                    CONF_ADDRESS: "000000",
                    CONF_ROLLING: 1,
                    CONF_REPEAT: 2,
                    CONF_OBSERVED_ADDRESSES: [],
                    CONF_POSITION: 0,
                    CONF_COVER_TYPE: "blind",
                    CONF_TIME_OUT: 30,
                    CONF_TIME_IN: 30,
                    CONF_MY_POSITION: 50,
                },
                include_id=False,
            ),
            errors=errors,
        )

    async def async_step_pick_edit_cover(self, user_input=None):
        """Pick which cover to edit."""
        cover_options = self._cover_options()
        if not cover_options:
            return self.async_abort(reason="no_covers")

        if user_input is not None:
            self._selected_cover_id = user_input[CONF_COVER_ID]
            return await self.async_step_edit_cover()

        return self.async_show_form(
            step_id="pick_edit_cover",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_COVER_ID): vol.In(cover_options),
                }
            ),
        )

    async def async_step_edit_cover(self, user_input=None):
        """Edit one existing cover.

        The cover id is intentionally not editable here. Changing it would create
        new entity unique_ids and leave stale entities while older v0/v2
        integrations are still running side by side.
        """
        errors = {}
        selected = self._get_selected_cover()

        if not selected:
            return self.async_abort(reason="cover_not_found")

        if user_input is not None:
            try:
                updated = self._normalize_form_cover(
                    user_input,
                    existing_id=selected[CONF_COVER_ID],
                )

                covers = [
                    updated if cover[CONF_COVER_ID] == selected[CONF_COVER_ID] else cover
                    for cover in self._current_covers()
                ]

                return self.async_create_entry(
                    title="",
                    data=self._base_options(covers),
                )
            except ValueError:
                errors["base"] = "invalid_cover"
            except Exception:
                errors["base"] = "invalid_cover"

        return self.async_show_form(
            step_id="edit_cover",
            data_schema=_cover_form_schema(selected, include_id=False),
            errors=errors,
            description_placeholders={
                "cover_name": selected[CONF_COVER_NAME],
                "cover_id": selected[CONF_COVER_ID],
            },
        )

    async def async_step_pick_remove_cover(self, user_input=None):
        """Pick which cover to remove."""
        cover_options = self._cover_options()
        if not cover_options:
            return self.async_abort(reason="no_covers")

        if user_input is not None:
            self._selected_cover_id = user_input[CONF_COVER_ID]
            return await self.async_step_remove_cover()

        return self.async_show_form(
            step_id="pick_remove_cover",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_COVER_ID): vol.In(cover_options),
                }
            ),
        )

    async def async_step_remove_cover(self, user_input=None):
        """Confirm removal of one cover."""
        selected = self._get_selected_cover()

        if not selected:
            return self.async_abort(reason="cover_not_found")

        if user_input is not None:
            if not user_input.get("confirm_remove", False):
                return await self.async_step_init()

            removed_cover_id = selected[CONF_COVER_ID]

            covers = [
                cover
                for cover in self._current_covers()
                if cover[CONF_COVER_ID] != removed_cover_id
            ]

            self._remove_cover_from_registries(removed_cover_id)

            return self.async_create_entry(
                title="",
                data=self._base_options(covers),
            )

        return self.async_show_form(
            step_id="remove_cover",
            data_schema=vol.Schema(
                {
                    vol.Required("confirm_remove", default=False): bool,
                }
            ),
            description_placeholders={
                "cover_name": selected[CONF_COVER_NAME],
                "cover_id": selected[CONF_COVER_ID],
            },
        )

    async def async_step_advanced_json(self, user_input=None):
        """Hidden fallback JSON editor for recovery.

        This step is deliberately not shown in the normal menu. It is kept so a
        developer can temporarily expose it again without reintroducing JSON into
        the normal user journey.
        """
        errors = {}
        current_covers = self._current_covers()

        if user_input is not None:
            try:
                normalized = normalize_covers_json(user_input[CONF_COVERS_JSON])
                return self.async_create_entry(
                    title="",
                    data=self._base_options(normalized),
                )
            except Exception:
                errors["base"] = "invalid_covers_json"

        return self.async_show_form(
            step_id="advanced_json",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_COVERS_JSON,
                        default=json.dumps(current_covers, indent=2),
                    ): selector.TextSelector(
                        selector.TextSelectorConfig(multiline=True)
                    ),
                }
            ),
            errors=errors,
        )
