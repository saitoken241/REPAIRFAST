from pydantic import BaseModel, EmailStr

class DepartmentBase(BaseModel):
    name: str
    


class DepartmentCreate(DepartmentBase):
    pass

class DepartmentResponse(DepartmentBase):
    id: int
    

    class Config:
        from_attributes = True