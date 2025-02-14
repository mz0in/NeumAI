from typing import List, Optional
from neumai.SinkConnectors.SinkConnector import SinkConnector
from neumai.Shared.NeumSinkInfo import NeumSinkInfo
from neumai.Shared.NeumVector  import NeumVector
from neumai.Shared.NeumSearch import NeumSearchResult
from neumai.Shared.Exceptions import(
    SupabaseConnectionException,
    SupabaseInsertionException,
    SupabaseIndexInfoException,
    SupabaseQueryException
)
from pydantic import Field
import vecs

class SupabaseSink(SinkConnector):
    """
    Supabase Sink

    A connector designed for exporting data to Supabase, a cloud-based database platform. It manages connections and data transfers to specific Supabase databases.

    Attributes:
    -----------
    database_connection : str
        Connection string or details required to connect to the Supabase database.

    collection_name : Optional[str]
        Optional name of the collection within Supabase where the data will be stored.
    """

    database_connection: str = Field(..., description="Database connection for Supabase.")

    collection_name: Optional[str] = Field(None, description="Optional collection name.")

    @property
    def sink_name(self) -> str:
        return 'SupabaseSink'
    
    @property
    def required_properties(self) -> List[str]:
        return ['database_connection']

    @property
    def optional_properties(self) -> List[str]:
        return ['collection_name']

    def validation(self) -> bool:
        """config_validation connector setup"""
        import vecs
        try:
            vx = vecs.create_client(self.database_connection)
        except Exception as e:
            raise SupabaseConnectionException(f"Supabase connection couldn't be initialized. See exception: {e}")
        return True 

    def store(self, pipeline_id: str, vectors_to_store:List[NeumVector], task_id:str = "") -> int:
        database_connection = self.database_connection
        vx = vecs.create_client(database_connection)
        try:
            collection_name = self.collection_name
            if collection_name == None: collection_name = f"pipeline_{pipeline_id}"
            dimensions = len(vectors_to_store[0].vector)
            db = vx.get_or_create_collection(name=collection_name, dimension=dimensions)
            to_upsert = []
            for i in range(0, len(vectors_to_store)):
                to_upsert.append((vectors_to_store[i].id, vectors_to_store[i].vector, vectors_to_store[i].metadata))

            db.upsert(records=to_upsert)
        except Exception as e:
            raise SupabaseInsertionException(f"Supabase storing failed. Exception {e}")
        finally:
            vx.disconnect()
        return len(vectors_to_store)
    
    def search(self, vector: List[float], number_of_results:int, pipeline_id:str) -> List:
        database_connection = self.database_connection
        vx = vecs.create_client(database_connection)
        collection_name = self.collection_name
        if collection_name == None: collection_name = f"pipeline_{pipeline_id}"
        try:
            db = vx.get_collection(name=collection_name)
        except:
            raise SupabaseQueryException(f"Collection {collection_name} does not exist")
        finally:
            vx.disconnect()
        try:
            results = db.query(
                data=vector,
                include_metadata=True,
                include_value=True,
                limit=number_of_results,
            )
        except Exception as e:
            raise SupabaseQueryException(f"Error querying vectors from Supabase. Exception: {e}")
        finally:
            vx.disconnect()
        matches = []
        for result in results:
            matches.append(NeumSearchResult(
                id= str(result[0]),
                metadata=result[2],
                score=result[1]
            ))
        
        return matches
    
    def info(self, pipeline_id: str) -> NeumSinkInfo:
        database_connection = self.database_connection
        vx = vecs.create_client(database_connection)
        collection_name = self.collection_name
        if collection_name == None: collection_name = f"pipeline_{pipeline_id}"
        try:
            db = vx.get_collection(name=collection_name)
        except:
            raise SupabaseIndexInfoException(f"Collection {collection_name} does not exist")
        finally:
            vx.disconnect()
        
        number_of_vectors = db.table.select('count(*)')[0].count

        return NeumSinkInfo(number_vectors_stored=number_of_vectors)