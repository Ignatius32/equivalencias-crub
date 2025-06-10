from app.models import Usuario
from app.services.keycloak_service import KeycloakService
from app import db
import os


class EvaluadorService:
    """Service to manage evaluators from both Keycloak and local database"""
    
    def __init__(self):
        self.keycloak_enabled = all([
            os.getenv('KEYCLOAK_SERVER_URL'),
            os.getenv('KEYCLOAK_REALM'),
            os.getenv('KEYCLOAK_CLIENT_ID'),
            os.getenv('KEYCLOAK_CLIENT_SECRET')
        ])
        
        if self.keycloak_enabled:
            try:
                self.keycloak_service = KeycloakService()
            except Exception as e:
                print(f"Error initializing Keycloak service: {str(e)}")
                self.keycloak_enabled = False
                self.keycloak_service = None
        else:
            self.keycloak_service = None
    
    def get_all_evaluadores(self):
        """Get all evaluators, preferring Keycloak data when available"""
        if self.keycloak_enabled and self.keycloak_service:
            try:
                print("DEBUG: EvaluadorService - fetching evaluadores from Keycloak")
                # Get evaluators from Keycloak and sync to local DB
                evaluadores = self.keycloak_service.get_evaluadores()
                if evaluadores:
                    print(f"DEBUG: EvaluadorService - found {len(evaluadores)} evaluadores from Keycloak")
                    return evaluadores
                else:
                    print("WARNING: EvaluadorService - no evaluadores found in Keycloak, falling back to local DB")
            except Exception as e:
                print(f"ERROR: EvaluadorService - error getting evaluators from Keycloak: {str(e)}")
        
        # Fallback to local database
        local_evaluadores = Usuario.query.filter_by(rol='evaluador').all()
        print(f"DEBUG: EvaluadorService - falling back to {len(local_evaluadores)} local evaluadores")
        return local_evaluadores
    
    def sync_evaluator_from_keycloak(self, keycloak_user_data):
        """Sync a single evaluator from Keycloak to local database"""
        if not keycloak_user_data:
            return None
        
        # Check if user exists locally
        user = Usuario.query.filter_by(keycloak_id=keycloak_user_data['id']).first()
        if not user:
            # Check by email
            user = Usuario.query.filter_by(email=keycloak_user_data.get('email', '')).first()
        
        if not user and keycloak_user_data.get('email'):
            # Create new user
            user = Usuario(
                username=keycloak_user_data.get('username', keycloak_user_data.get('email')),
                email=keycloak_user_data.get('email'),
                nombre=keycloak_user_data.get('firstName', ''),
                apellido=keycloak_user_data.get('lastName', ''),
                rol='evaluador',
                keycloak_id=keycloak_user_data['id'],
                is_keycloak_user=True
            )
            db.session.add(user)
        elif user:
            # Update existing user
            user.keycloak_id = keycloak_user_data['id']
            user.is_keycloak_user = True
            user.rol = 'evaluador'  # Ensure role is correct
            user.nombre = keycloak_user_data.get('firstName', user.nombre)
            user.apellido = keycloak_user_data.get('lastName', user.apellido)
            user.email = keycloak_user_data.get('email', user.email)
        
        try:
            db.session.commit()
            return user
        except Exception as e:
            db.session.rollback()
            print(f"Error syncing evaluator: {str(e)}")
            return None
    
    def get_evaluador_by_id(self, evaluador_id):
        """Get evaluator by ID"""
        return Usuario.query.filter_by(id=evaluador_id, rol='evaluador').first()
    
    def get_evaluadores_with_workload(self, auto_sync=True):
        """Get all evaluators with their current workload (number of assigned solicitudes)"""
        from app.models import SolicitudEquivalencia
        
        # Auto-sync evaluadores from Keycloak if enabled and requested
        if auto_sync and self.keycloak_enabled and self.keycloak_service:
            try:
                print("DEBUG: Auto-syncing evaluadores from Keycloak")
                self.keycloak_service.sync_all_evaluadores()
            except Exception as e:
                print(f"WARNING: Auto-sync failed, continuing with local data: {str(e)}")
        
        evaluadores = self.get_all_evaluadores()
        evaluadores_with_workload = []
        
        for evaluador in evaluadores:
            # Count assigned active solicitudes (not resolved)
            workload = SolicitudEquivalencia.query.filter(
                SolicitudEquivalencia.evaluador_id == evaluador.id,
                SolicitudEquivalencia.estado.in_(['pendiente', 'en_evaluacion'])
            ).count()
            
            evaluadores_with_workload.append({
                'evaluador': evaluador,
                'workload': workload,
                'total_assigned': SolicitudEquivalencia.query.filter_by(evaluador_id=evaluador.id).count()
            })
        
        # Sort by workload (ascending) so evaluators with less work appear first
        evaluadores_with_workload.sort(key=lambda x: x['workload'])
        
        return evaluadores_with_workload
    
    def suggest_evaluador(self):
        """Suggest an evaluator based on current workload"""
        evaluadores_with_workload = self.get_evaluadores_with_workload()
        
        if evaluadores_with_workload:
            # Return evaluator with least workload
            return evaluadores_with_workload[0]['evaluador']
        
        return None
    
    def assign_evaluador_to_solicitud(self, solicitud_id, evaluador_id):
        """Assign an evaluator to a solicitud"""
        from app.models import SolicitudEquivalencia
        
        solicitud = SolicitudEquivalencia.query.get(solicitud_id)
        evaluador = self.get_evaluador_by_id(evaluador_id)
        
        if not solicitud:
            return False, "Solicitud no encontrada"
        
        if not evaluador:
            return False, "Evaluador no encontrado"
        
        try:
            solicitud.evaluador_id = evaluador.id
            # Change state to 'en_evaluacion' if it was 'pendiente'
            if solicitud.estado == 'pendiente':
                solicitud.estado = 'en_evaluacion'
            
            db.session.commit()
            return True, f"Evaluador {evaluador.nombre} {evaluador.apellido} asignado correctamente"
        except Exception as e:
            db.session.rollback()
            return False, f"Error al asignar evaluador: {str(e)}"
    
    def unassign_evaluador_from_solicitud(self, solicitud_id):
        """Remove evaluator assignment from a solicitud"""
        from app.models import SolicitudEquivalencia
        
        solicitud = SolicitudEquivalencia.query.get(solicitud_id)
        
        if not solicitud:
            return False, "Solicitud no encontrada"
        
        try:
            solicitud.evaluador_id = None
            # Optionally change state back to 'pendiente' if no dictamenes exist
            if not solicitud.dictamenes:
                solicitud.estado = 'pendiente'
            
            db.session.commit()
            return True, "Evaluador desasignado correctamente"
        except Exception as e:
            db.session.rollback()
            return False, f"Error al desasignar evaluador: {str(e)}"

    def is_keycloak_enabled(self):
        """Check if Keycloak is enabled"""
        return self.keycloak_enabled

    def force_sync_evaluadores(self):
        """Force sync all evaluadores from Keycloak"""
        if self.keycloak_enabled and self.keycloak_service:
            try:
                return self.keycloak_service.force_refresh_evaluadores()
            except Exception as e:
                print(f"Error in force sync evaluadores: {str(e)}")
                return []
        return []

    def get_evaluadores_stats(self):
        """Get statistics about evaluadores"""
        if self.keycloak_enabled:
            keycloak_count = len(self.keycloak_service.get_users_by_role('evaluador')) if self.keycloak_service else 0
        else:
            keycloak_count = 0
            
        local_count = Usuario.query.filter_by(rol='evaluador').count()
        local_keycloak_count = Usuario.query.filter_by(rol='evaluador', is_keycloak_user=True).count()
        
        return {
            'keycloak_count': keycloak_count,
            'local_count': local_count,
            'local_keycloak_count': local_keycloak_count,
            'keycloak_enabled': self.keycloak_enabled
        }

    def ensure_fresh_evaluadores(self):
        """Ensure we have fresh evaluador data from Keycloak"""
        if self.keycloak_enabled and self.keycloak_service:
            try:
                print("DEBUG: Ensuring fresh evaluadores data from Keycloak")
                return self.keycloak_service.sync_all_evaluadores()
            except Exception as e:
                print(f"WARNING: Could not refresh evaluadores from Keycloak: {str(e)}")
                # Return local evaluadores as fallback
                return Usuario.query.filter_by(rol='evaluador').all()
        else:
            return Usuario.query.filter_by(rol='evaluador').all()

    def get_evaluadores_for_selection(self):
        """Get evaluadores specifically for admin/depto selection dropdowns"""
        return self.get_evaluadores_with_workload(auto_sync=True)

    def get_service_status(self):
        """Get comprehensive service status"""
        status = {
            'keycloak_enabled': self.keycloak_enabled,
            'keycloak_status': None,
            'local_evaluadores': Usuario.query.filter_by(rol='evaluador').count(),
            'keycloak_evaluadores': 0
        }
        
        if self.keycloak_enabled and self.keycloak_service:
            status['keycloak_status'] = self.keycloak_service.get_service_status()
            if status['keycloak_status'].get('can_access_users'):
                status['keycloak_evaluadores'] = status['keycloak_status'].get('evaluador_count', 0)
        
        return status
