"""Loader agent."""

from llama_index.llms import ChatMessage
from llama_index.prompts import ChatPromptTemplate
from typing import List, cast, Optional
from llama_index.tools import FunctionTool
from llama_index.agent.types import BaseAgent
from core.builder_config import BUILDER_LLM
from typing import Dict, Tuple, Any, Callable, Union
import streamlit as st
from pathlib import Path
import json
import uuid
from core.constants import AGENT_CACHE_DIR
import shutil

from core.param_cache import ParamCache, RAGParams
from core.utils import (
    load_data,
    get_tool_objects,
    construct_agent,
    load_meta_agent,
)
from core.agent_builder.registry import AgentCacheRegistry
from core.agent_builder.base import RAGAgentBuilder
from core.agent_builder.multimodal import MultimodalRAGAgentBuilder

####################
#### META Agent ####
####################

RAG_BUILDER_SYS_STR = """\
You are helping to construct an agent given a user-specified task. 
You should generally use the tools in this rough order to build the agent.

1) Create system prompt tool: to create the system prompt for the agent.
2) Load in user-specified data (based on file paths they specify).
3) Decide whether or not to add additional tools.
4) Set parameters for the RAG pipeline.
5) Build the agent

This will be a back and forth conversation with the user. You should
continue asking users if there's anything else they want to do until
they say they're done. To help guide them on the process, 
you can give suggestions on parameters they can set based on the tools they
have available (e.g. "Do you want to set the number of documents to retrieve?")

"""


### DEFINE Agent ####
# NOTE: here we define a function that is dependent on the LLM,
# please make sure to update the LLM above if you change the function below


def _get_builder_agent_tools(agent_builder: RAGAgentBuilder) -> List[FunctionTool]:
    """Get list of builder agent tools to pass to the builder agent."""
    # see if metaphor api key is set, otherwise don't add web tool
    # TODO: refactor this later

    if "metaphor_key" in st.secrets:
        fns: List[Callable] = [
            agent_builder.create_system_prompt,
            agent_builder.load_data,
            agent_builder.add_web_tool,
            agent_builder.get_rag_params,
            agent_builder.set_rag_params,
            agent_builder.create_agent,
        ]
    else:
        fns = [
            agent_builder.create_system_prompt,
            agent_builder.load_data,
            agent_builder.get_rag_params,
            agent_builder.set_rag_params,
            agent_builder.create_agent,
        ]

    fn_tools: List[FunctionTool] = [FunctionTool.from_defaults(fn=fn) for fn in fns]
    return fn_tools


def _get_mm_builder_agent_tools(agent_builder: MultimodalRAGAgentBuilder) -> List[FunctionTool]:
    """Get list of builder agent tools to pass to the builder agent."""
    fns = [
        agent_builder.create_system_prompt,
        agent_builder.load_data,
        agent_builder.get_rag_params,
        agent_builder.set_rag_params,
        agent_builder.create_agent,
    ]

    fn_tools: List[FunctionTool] = [FunctionTool.from_defaults(fn=fn) for fn in fns]
    return fn_tools


# define agent
def load_meta_agent_and_tools(
    cache: Optional[ParamCache] = None,
    agent_registry: Optional[AgentCacheRegistry] = None,
    is_multimodal: bool = False,
) -> Tuple[BaseAgent, RAGAgentBuilder]:
    """Load meta agent and tools."""

    if is_multimodal:
        agent_builder = MultimodalRAGAgentBuilder(cache, agent_registry=agent_registry)
        fn_tools = _get_mm_builder_agent_tools(agent_builder)
        builder_agent = load_meta_agent(
            fn_tools, llm=BUILDER_LLM, system_prompt=RAG_BUILDER_SYS_STR, verbose=True
        )
    else:
        # think of this as tools for the agent to use
        agent_builder = RAGAgentBuilder(cache, agent_registry=agent_registry)
        fn_tools = _get_builder_agent_tools(agent_builder)
        builder_agent = load_meta_agent(
            fn_tools, llm=BUILDER_LLM, system_prompt=RAG_BUILDER_SYS_STR, verbose=True
        )

    return builder_agent, agent_builder