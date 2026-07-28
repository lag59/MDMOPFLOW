from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import RequestContext, require_permissions
from app.models import AuditLog, Customer, Employee, Equipment, Material, Truck
from app.schemas import (
    CustomerCreate,
    CustomerResponse,
    CustomerUpdate,
    EmployeeCreate,
    EmployeeResponse,
    EmployeeUpdate,
    EquipmentCreate,
    EquipmentResponse,
    EquipmentUpdate,
    MaterialCreate,
    MaterialResponse,
    MaterialUpdate,
    TruckCreate,
    TruckResponse,
    TruckUpdate,
)

router = APIRouter(prefix="/api", tags=["Core Platform"])


def _tenant_scope(context: RequestContext, db: Session, model: type[Customer] | type[Employee] | type[Equipment] | type[Material] | type[Truck]):
    if not context.membership:
        raise HTTPException(status_code=400, detail="X-Tenant-ID is required")
    return select(model).where(model.tenant_id == context.membership.tenant_id)


@router.get("/customers", response_model=list[CustomerResponse], operation_id="customers_list", summary="List customers")
def list_customers(context: RequestContext = Depends(require_permissions("project_read")), db: Session = Depends(get_db)):
    query = _tenant_scope(context, db, Customer)
    return db.scalars(query.order_by(Customer.name.asc())).all()


@router.post("/customers", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED, operation_id="customers_create", summary="Create customer")
def create_customer(payload: CustomerCreate, context: RequestContext = Depends(require_permissions("project_write")), db: Session = Depends(get_db)):
    item = Customer(tenant_id=context.membership.tenant_id if context.membership else "", name=payload.name, contact_name=payload.contact_name, email=payload.email, phone=payload.phone, address=payload.address, notes=payload.notes, created_by=context.user.id)
    db.add(item)
    db.flush()
    db.add(AuditLog(tenant_id=item.tenant_id, actor_user_id=context.user.id, action="create_customer", resource_type="customer", resource_id=item.id, details=item.name, created_by=context.user.id))
    db.commit()
    db.refresh(item)
    return item


@router.get("/customers/{customer_id}", response_model=CustomerResponse, operation_id="customers_get", summary="Get customer")
def get_customer(customer_id: str, context: RequestContext = Depends(require_permissions("project_read")), db: Session = Depends(get_db)):
    item = db.get(Customer, customer_id)
    if not item or (context.membership and item.tenant_id != context.membership.tenant_id):
        raise HTTPException(status_code=404, detail="Customer not found")
    return item


@router.patch("/customers/{customer_id}", response_model=CustomerResponse, operation_id="customers_update", summary="Update customer")
def update_customer(customer_id: str, payload: CustomerUpdate, context: RequestContext = Depends(require_permissions("project_write")), db: Session = Depends(get_db)):
    item = db.get(Customer, customer_id)
    if not item or (context.membership and item.tenant_id != context.membership.tenant_id):
        raise HTTPException(status_code=404, detail="Customer not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return item


@router.get("/employees", response_model=list[EmployeeResponse], operation_id="employees_list", summary="List employees")
def list_employees(context: RequestContext = Depends(require_permissions("project_read")), db: Session = Depends(get_db)):
    query = _tenant_scope(context, db, Employee)
    return db.scalars(query.order_by(Employee.name.asc())).all()


@router.post("/employees", response_model=EmployeeResponse, status_code=status.HTTP_201_CREATED, operation_id="employees_create", summary="Create employee")
def create_employee(payload: EmployeeCreate, context: RequestContext = Depends(require_permissions("project_write")), db: Session = Depends(get_db)):
    item = Employee(tenant_id=context.membership.tenant_id if context.membership else "", name=payload.name, role_title=payload.role_title, email=payload.email, phone=payload.phone, department=payload.department, status=payload.status, created_by=context.user.id)
    db.add(item)
    db.flush()
    db.add(AuditLog(tenant_id=item.tenant_id, actor_user_id=context.user.id, action="create_employee", resource_type="employee", resource_id=item.id, details=item.name, created_by=context.user.id))
    db.commit()
    db.refresh(item)
    return item


@router.get("/employees/{employee_id}", response_model=EmployeeResponse, operation_id="employees_get", summary="Get employee")
def get_employee(employee_id: str, context: RequestContext = Depends(require_permissions("project_read")), db: Session = Depends(get_db)):
    item = db.get(Employee, employee_id)
    if not item or (context.membership and item.tenant_id != context.membership.tenant_id):
        raise HTTPException(status_code=404, detail="Employee not found")
    return item


@router.patch("/employees/{employee_id}", response_model=EmployeeResponse, operation_id="employees_update", summary="Update employee")
def update_employee(employee_id: str, payload: EmployeeUpdate, context: RequestContext = Depends(require_permissions("project_write")), db: Session = Depends(get_db)):
    item = db.get(Employee, employee_id)
    if not item or (context.membership and item.tenant_id != context.membership.tenant_id):
        raise HTTPException(status_code=404, detail="Employee not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return item


@router.get("/equipment", response_model=list[EquipmentResponse], operation_id="equipment_list", summary="List equipment")
def list_equipment(context: RequestContext = Depends(require_permissions("project_read")), db: Session = Depends(get_db)):
    query = _tenant_scope(context, db, Equipment)
    return db.scalars(query.order_by(Equipment.name.asc())).all()


@router.post("/equipment", response_model=EquipmentResponse, status_code=status.HTTP_201_CREATED, operation_id="equipment_create", summary="Create equipment")
def create_equipment(payload: EquipmentCreate, context: RequestContext = Depends(require_permissions("project_write")), db: Session = Depends(get_db)):
    item = Equipment(tenant_id=context.membership.tenant_id if context.membership else "", name=payload.name, equipment_type=payload.equipment_type, capacity_tons=payload.capacity_tons, status=payload.status, notes=payload.notes, created_by=context.user.id)
    db.add(item)
    db.flush()
    db.add(AuditLog(tenant_id=item.tenant_id, actor_user_id=context.user.id, action="create_equipment", resource_type="equipment", resource_id=item.id, details=item.name, created_by=context.user.id))
    db.commit()
    db.refresh(item)
    return item


@router.get("/equipment/{equipment_id}", response_model=EquipmentResponse, operation_id="equipment_get", summary="Get equipment")
def get_equipment(equipment_id: str, context: RequestContext = Depends(require_permissions("project_read")), db: Session = Depends(get_db)):
    item = db.get(Equipment, equipment_id)
    if not item or (context.membership and item.tenant_id != context.membership.tenant_id):
        raise HTTPException(status_code=404, detail="Equipment not found")
    return item


@router.patch("/equipment/{equipment_id}", response_model=EquipmentResponse, operation_id="equipment_update", summary="Update equipment")
def update_equipment(equipment_id: str, payload: EquipmentUpdate, context: RequestContext = Depends(require_permissions("project_write")), db: Session = Depends(get_db)):
    item = db.get(Equipment, equipment_id)
    if not item or (context.membership and item.tenant_id != context.membership.tenant_id):
        raise HTTPException(status_code=404, detail="Equipment not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return item


@router.get("/trucks", response_model=list[TruckResponse], operation_id="trucks_list", summary="List trucks")
def list_trucks(context: RequestContext = Depends(require_permissions("project_read")), db: Session = Depends(get_db)):
    query = _tenant_scope(context, db, Truck)
    return db.scalars(query.order_by(Truck.unit_number.asc())).all()


@router.post("/trucks", response_model=TruckResponse, status_code=status.HTTP_201_CREATED, operation_id="trucks_create", summary="Create truck")
def create_truck(payload: TruckCreate, context: RequestContext = Depends(require_permissions("project_write")), db: Session = Depends(get_db)):
    item = Truck(tenant_id=context.membership.tenant_id if context.membership else "", unit_number=payload.unit_number, truck_type=payload.truck_type, capacity_tons=payload.capacity_tons, status=payload.status, assigned_driver=payload.assigned_driver, notes=payload.notes, created_by=context.user.id)
    db.add(item)
    db.flush()
    db.add(AuditLog(tenant_id=item.tenant_id, actor_user_id=context.user.id, action="create_truck", resource_type="truck", resource_id=item.id, details=item.unit_number, created_by=context.user.id))
    db.commit()
    db.refresh(item)
    return item


@router.get("/trucks/{truck_id}", response_model=TruckResponse, operation_id="trucks_get", summary="Get truck")
def get_truck(truck_id: str, context: RequestContext = Depends(require_permissions("project_read")), db: Session = Depends(get_db)):
    item = db.get(Truck, truck_id)
    if not item or (context.membership and item.tenant_id != context.membership.tenant_id):
        raise HTTPException(status_code=404, detail="Truck not found")
    return item


@router.patch("/trucks/{truck_id}", response_model=TruckResponse, operation_id="trucks_update", summary="Update truck")
def update_truck(truck_id: str, payload: TruckUpdate, context: RequestContext = Depends(require_permissions("project_write")), db: Session = Depends(get_db)):
    item = db.get(Truck, truck_id)
    if not item or (context.membership and item.tenant_id != context.membership.tenant_id):
        raise HTTPException(status_code=404, detail="Truck not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return item


@router.get("/materials", response_model=list[MaterialResponse], operation_id="materials_list", summary="List materials")
def list_materials(context: RequestContext = Depends(require_permissions("project_read")), db: Session = Depends(get_db)):
    query = _tenant_scope(context, db, Material)
    return db.scalars(query.order_by(Material.name.asc())).all()


@router.post("/materials", response_model=MaterialResponse, status_code=status.HTTP_201_CREATED, operation_id="materials_create", summary="Create material")
def create_material(payload: MaterialCreate, context: RequestContext = Depends(require_permissions("project_write")), db: Session = Depends(get_db)):
    item = Material(tenant_id=context.membership.tenant_id if context.membership else "", name=payload.name, unit_of_measure=payload.unit_of_measure, density_tons_per_cubic_yard=payload.density_tons_per_cubic_yard, description=payload.description, created_by=context.user.id)
    db.add(item)
    db.flush()
    db.add(AuditLog(tenant_id=item.tenant_id, actor_user_id=context.user.id, action="create_material", resource_type="material", resource_id=item.id, details=item.name, created_by=context.user.id))
    db.commit()
    db.refresh(item)
    return item


@router.get("/materials/{material_id}", response_model=MaterialResponse, operation_id="materials_get", summary="Get material")
def get_material(material_id: str, context: RequestContext = Depends(require_permissions("project_read")), db: Session = Depends(get_db)):
    item = db.get(Material, material_id)
    if not item or (context.membership and item.tenant_id != context.membership.tenant_id):
        raise HTTPException(status_code=404, detail="Material not found")
    return item


@router.patch("/materials/{material_id}", response_model=MaterialResponse, operation_id="materials_update", summary="Update material")
def update_material(material_id: str, payload: MaterialUpdate, context: RequestContext = Depends(require_permissions("project_write")), db: Session = Depends(get_db)):
    item = db.get(Material, material_id)
    if not item or (context.membership and item.tenant_id != context.membership.tenant_id):
        raise HTTPException(status_code=404, detail="Material not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return item
