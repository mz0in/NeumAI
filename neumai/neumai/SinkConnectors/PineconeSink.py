from typing import List, Optional
from neumai.Shared.NeumSearch import NeumSearchResult
from neumai.Shared.NeumSinkInfo import NeumSinkInfo
from neumai.SinkConnectors.SinkConnector import SinkConnector
from neumai.Shared.NeumVector  import NeumVector
from neumai.Shared.Exceptions import (
    PineconeConnectionException,
    PineconeInsertionException,
    PineconeIndexInfoException,
    PineconeQueryException,
)
from pydantic import Field
import pinecone

class  PineconeSink(SinkConnector):
    """
    Pinecone Sink

    A sink connector specifically designed for Pinecone, facilitating the output of processed data into a Pinecone environment.

    Attributes:
    -----------
    api_key : str
        API key for accessing the Pinecone service.

    environment : str
        The specific Pinecone environment to connect to.

    index : str
        The index in Pinecone where the data will be stored.

    namespace : Optional[str]
        Optional namespace within the Pinecone environment. Used for organizing data.
    """

    api_key: str = Field(..., description="API key for Pinecone.")

    environment: str = Field(..., description="Pinecone environment.")

    index: str = Field(..., description="Index for Pinecone.")

    namespace: Optional[str] = Field(None, description="Optional namespace.")

    @property
    def sink_name(self) -> str:
        return 'PineconeSink'
    
    @property
    def required_properties(self) -> List[str]:
        return ['api_key', 'environment', 'index']

    @property
    def optional_properties(self) -> List[str]:
        return ['namespace']

    def validation(self) -> bool:
        """config_validation connector setup"""
        import pinecone
        try:
            pinecone.init(api_key=self.api_key, environment=self.environment)    
            index = pinecone.Index(index_name=self.index)
            index.describe_index_stats()
        except Exception as e:
            raise PineconeConnectionException(f"Pinecone connection couldn't be initialized. See exception: {e}")
        return True 

    def store(self, pipeline_id: str, vectors_to_store:List[NeumVector], task_id:str = "") -> int:
        api_key =  self.api_key
        environment = self.environment
        index = self.index
        namespace = self.namespace
        if namespace == None: namespace = f"pipeline_{pipeline_id}"

        try:
            pinecone.init(api_key=api_key, environment=environment)    
            index = pinecone.Index(index_name=index)
            batch_size = 32 # how does changing this affect ?
            vectors_stored = 0
            for i in range(0, len(vectors_to_store), batch_size):
                # set end position of batch
                i_end = min(i + batch_size, len(vectors_to_store))
                # get batch of texts and ids
                vector_batch = vectors_to_store[i:i_end]
                to_upsert = [(vector.id, vector.vector, vector.metadata) for vector in vector_batch]
                result = index.upsert(vectors=to_upsert, namespace=namespace)
                vectors_stored += result['upserted_count'] 
        except Exception as e:
            raise PineconeInsertionException(f"Failed to store in Pinecone. Exception - {e}")
        return int(vectors_stored)
    
    def search(self, vector: List[float], number_of_results:int, pipeline_id:str) -> List[NeumSearchResult]:
        import pinecone
        api_key =  self.api_key
        environment = self.environment
        index = self.index
        namespace = self.namespace
        if namespace == None: namespace = f"pipeline_{pipeline_id}"

        try:
            pinecone.init(      
                api_key=api_key,      
                environment=environment)    
            index = pinecone.Index(index)
            results = index.query(vector=vector, top_k=number_of_results, namespace=namespace, include_values=False, include_metadata=True)["matches"]
        except Exception as e:
            raise PineconeQueryException(f"Failed to query pinecone. Exception - {e}")
        
        matches = []
        for result in results:
            matches.append(NeumSearchResult(id= result["id"], metadata=result["metadata"], score=result["score"]))
        return matches
    
    def info(self, pipeline_id: str) -> NeumSinkInfo:
        import pinecone
        api_key =  self.api_key
        environment = self.environment
        index = self.index
        namespace = self.namespace
        if namespace == None: namespace = f"pipeline_{pipeline_id}"
        
        try:
            pinecone.init(      
                api_key=api_key,      
                environment=environment)    
            index = pinecone.Index(index)
            namespaces = index.describe_index_stats()["namespace"]
            if namespace in namespaces:
                return NeumSinkInfo(number_vectors_stored=namespaces[namespace]["vector_count"])
        except Exception as e:
            raise PineconeIndexInfoException(f"Failed to get info for pinecone. Exception - {e}")