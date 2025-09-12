from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime
import uuid
import structlog
from config.database import get_db
from models.database_models import AgentExecution

logger = structlog.get_logger()

class BaseAgent(ABC):
    def __init__(self, name: str):
        self.name = name
        self.execution_id = str(uuid.uuid4())
        
    @abstractmethod
    async def execute(self, input_data: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """Execute the agent's main functionality"""
        pass
    
    async def run(self, input_data: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """Wrapper method that handles logging and database recording"""
        start_time = datetime.utcnow()
        
        try:
            logger.info(f"Starting agent {self.name}", 
                       session_id=session_id, 
                       agent=self.name,
                       execution_id=self.execution_id)
            
            result = await self.execute(input_data, session_id)
            
            end_time = datetime.utcnow()
            execution_time_ms = int((end_time - start_time).total_seconds() * 1000)
            
            # Log to database
            await self._log_execution(session_id, input_data, result, 
                                    execution_time_ms, "success")
            
            logger.info(f"Completed agent {self.name}", 
                       session_id=session_id,
                       agent=self.name,
                       execution_time_ms=execution_time_ms)
            
            return result
            
        except Exception as e:
            end_time = datetime.utcnow()
            execution_time_ms = int((end_time - start_time).total_seconds() * 1000)
            
            error_message = str(e)
            
            # Log error to database
            await self._log_execution(session_id, input_data, {}, 
                                    execution_time_ms, "error", error_message)
            
            logger.error(f"Agent {self.name} failed", 
                        session_id=session_id,
                        agent=self.name,
                        error=error_message,
                        execution_time_ms=execution_time_ms)
            
            raise
    
    def log(self, message: str, **kwargs):
        """Simple logging method for agents"""
        logger.info(message, agent=self.name, **kwargs)
    
    async def _log_execution(self, session_id: str, input_data: Dict[str, Any], 
                           output_data: Dict[str, Any], execution_time_ms: int,
                           status: str, error_message: Optional[str] = None):
        """Log agent execution to database"""
        db = next(get_db())
        try:
            execution = AgentExecution(
                session_id=session_id,
                agent_name=self.name,
                input_data=input_data,
                output_data=output_data,
                execution_time_ms=execution_time_ms,
                status=status,
                error_message=error_message
            )
            db.add(execution)
            db.commit()
        except Exception as e:
            logger.error(f"Failed to log execution for {self.name}", error=str(e))
        finally:
            db.close()
    
    def validate_input(self, input_data: Dict[str, Any], required_fields: list) -> None:
        """Validate that required fields are present in input"""
        missing_fields = [field for field in required_fields if field not in input_data]
        if missing_fields:
            raise ValueError(f"Missing required fields: {missing_fields}")
    
    def format_output(self, data: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Standard output format for all agents"""
        output = {
            "agent": self.name,
            "execution_id": self.execution_id,
            "timestamp": datetime.utcnow().isoformat(),
            "data": data
        }
        
        if metadata:
            output["metadata"] = metadata
            
        return output