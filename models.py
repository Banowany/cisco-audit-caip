from pydantic import BaseModel
from typing import List


class CiscoConfigPath(BaseModel):
    lines: List[str]